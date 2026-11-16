// C++17 CLI：執行同目錄的 hello.py，保留輸出、逾時與嚴格比對結果。
#include <algorithm>
#include <chrono>
#include <cmath>
#include <cstdio>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <iostream>
#include <memory>
#include <stdexcept>
#include <string>
#include <thread>
#include <vector>
#ifdef _WIN32
#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <windows.h>
#include <io.h>
#include <fcntl.h>
#include <shellapi.h>
#ifdef _MSC_VER
#pragma comment(lib, "shell32.lib")
#endif
#else
#include <cerrno>
#include <csignal>
#include <sys/wait.h>
#include <unistd.h>
#endif

namespace fs = std::filesystem;
using Clock = std::chrono::steady_clock;

// 驗證 UTF-8，拒絕過長編碼、代理碼與超出 Unicode 範圍的碼點。
bool valid_utf8(const std::string& s) {
    for (size_t i = 0; i < s.size();) {
        unsigned char c = s[i++];
        if (c < 128) continue;
        unsigned count, value, minimum;
        if (c >= 0xc2 && c <= 0xdf) { count = 1; value = c & 31; minimum = 128; }
        else if (c >= 0xe0 && c <= 0xef) { count = 2; value = c & 15; minimum = 2048; }
        else if (c >= 0xf0 && c <= 0xf4) { count = 3; value = c & 7; minimum = 65536; }
        else return false;
        if (s.size() - i < count) return false;
        while (count--) {
            unsigned char next = s[i++];
            if ((next & 0xc0) != 0x80) return false;
            value = (value << 6) | (next & 63);
        }
        if (value < minimum || value > 0x10ffff || (value >= 0xd800 && value <= 0xdfff)) return false;
    }
    return true;
}

std::string normalize_output(const std::string& text) {
    std::string result;
    for (size_t i = 0; i < text.size(); ++i) {
        if (text[i] == '\r') {
            result += '\n';
            if (i + 1 < text.size() && text[i + 1] == '\n') ++i;
        } else result += text[i];
    }
    if (!result.empty() && result.back() == '\n') result.pop_back();
    return result;
}

fs::path expand_home(const std::string& value) {
    if (value == "~" || value.rfind("~/", 0) == 0 || value.rfind("~\\", 0) == 0) {
#ifdef _WIN32
        const char* home = std::getenv("USERPROFILE");
#else
        const char* home = std::getenv("HOME");
#endif
        if (home) return fs::u8path(home) / fs::u8path(value.size() > 2 ? value.substr(2) : "");
    }
    return fs::u8path(value);
}

std::string read_test_file(const fs::path& path) {
    std::ifstream file(path, std::ios::binary);
    if (!file) throw std::runtime_error("無法讀取檔案：" + path.u8string());
    std::string text((std::istreambuf_iterator<char>(file)), {});
    if (file.bad()) throw std::runtime_error("無法讀取檔案：" + path.u8string());
    if (text.compare(0, 3, "\xef\xbb\xbf") == 0) text.erase(0, 3);
    if (!valid_utf8(text)) throw std::runtime_error("無法讀取檔案（測資須為 UTF-8）");
    return text;
}

// 使用匿名暫存檔重導標準串流，避免大量輸入或輸出塞滿管線而死鎖。
struct TempFile {
    FILE* file = nullptr;
    TempFile() {
#ifdef _WIN32
        wchar_t directory[MAX_PATH + 1], name[MAX_PATH + 1];
        DWORD length = GetTempPathW(MAX_PATH + 1, directory);
        if (!length || length > MAX_PATH || !GetTempFileNameW(directory, L"val", 0, name))
            throw std::runtime_error("無法建立暫存檔");
        HANDLE handle = CreateFileW(name, GENERIC_READ | GENERIC_WRITE,
                                    FILE_SHARE_READ | FILE_SHARE_WRITE | FILE_SHARE_DELETE,
                                    nullptr, OPEN_EXISTING, FILE_ATTRIBUTE_TEMPORARY | FILE_FLAG_DELETE_ON_CLOSE, nullptr);
        if (handle == INVALID_HANDLE_VALUE) {
            DeleteFileW(name);
            throw std::runtime_error("無法開啟暫存檔");
        }
        int fd = _open_osfhandle(reinterpret_cast<intptr_t>(handle), _O_RDWR | _O_BINARY);
        if (fd < 0) CloseHandle(handle);
        else {
            file = _fdopen(fd, "w+b");
            if (!file) _close(fd);
        }
#else
        file = std::tmpfile();
#endif
        if (!file) throw std::runtime_error("無法建立暫存檔");
    }
    ~TempFile() { std::fclose(file); }
    TempFile(const TempFile&) = delete;
    TempFile& operator=(const TempFile&) = delete;
    std::string read() {
        std::rewind(file);
        std::string text;
        char buffer[8192];
        size_t n;
        while ((n = std::fread(buffer, 1, sizeof buffer, file))) text.append(buffer, n);
        if (std::ferror(file)) throw std::runtime_error("無法讀取暫存輸出");
        return text;
    }
};

struct Result {
    std::string out, err;
    long long code = -1;
    bool timeout = false;
    double elapsed = 0;
};

#ifdef _WIN32
// 遵循 Windows 命令列的引號與反斜線規則，不經過 shell。
std::wstring quote(const std::wstring& text) {
    std::wstring result = L"\"";
    size_t slashes = 0;
    for (wchar_t c : text) {
        if (c == L'\\') { ++slashes; continue; }
        result.append(c == L'"' ? slashes * 2 + 1 : slashes, L'\\');
        result += c;
        slashes = 0;
    }
    result.append(slashes * 2, L'\\');
    return result + L'"';
}
#endif

Result run(const fs::path& script, const std::string& python, const std::string& input, double timeout) {
    TempFile in, out, err;
    if (std::fwrite(input.data(), 1, input.size(), in.file) != input.size())
        throw std::runtime_error("無法寫入測資暫存檔");
    std::rewind(in.file);
    Result result;
    auto start = Clock::now();
#ifdef _WIN32
    STARTUPINFOW startup{};
    startup.cb = sizeof startup;
    startup.dwFlags = STARTF_USESTDHANDLES;
    HANDLE handles[3]{};
    FILE* files[] = {in.file, out.file, err.file};
    for (int i = 0; i < 3; ++i) {
        if (!DuplicateHandle(GetCurrentProcess(), reinterpret_cast<HANDLE>(_get_osfhandle(_fileno(files[i]))),
                             GetCurrentProcess(), &handles[i], 0, TRUE, DUPLICATE_SAME_ACCESS)) {
            for (HANDLE h : handles) if (h) CloseHandle(h);
            throw std::runtime_error("無法建立子程序串流");
        }
    }
    startup.hStdInput = handles[0]; startup.hStdOutput = handles[1]; startup.hStdError = handles[2];
    PROCESS_INFORMATION process{};
    std::wstring command = quote(fs::u8path(python).wstring()) + L" -X utf8 " + quote(script.wstring());
    BOOL created = CreateProcessW(nullptr, command.data(), nullptr, nullptr, TRUE, CREATE_NO_WINDOW,
                                  nullptr, script.parent_path().c_str(), &startup, &process);
    DWORD launch_error = created ? 0 : GetLastError();
    for (HANDLE h : handles) CloseHandle(h);
    if (!created) throw std::runtime_error("無法啟動執行檔，Windows 錯誤：" + std::to_string(launch_error));
    CloseHandle(process.hThread);
    while (WaitForSingleObject(process.hProcess, 10) == WAIT_TIMEOUT) {
        if (std::chrono::duration<double>(Clock::now() - start).count() >= timeout) {
            result.timeout = true;
            TerminateProcess(process.hProcess, 1);
            WaitForSingleObject(process.hProcess, INFINITE);
            break;
        }
    }
    DWORD code;
    if (GetExitCodeProcess(process.hProcess, &code) && !result.timeout) result.code = code;
    CloseHandle(process.hProcess);
#else
    pid_t pid = fork();
    if (pid < 0) throw std::runtime_error("無法啟動執行檔：fork 失敗");
    if (pid == 0) {
        if (dup2(fileno(in.file), STDIN_FILENO) < 0 || dup2(fileno(out.file), STDOUT_FILENO) < 0 ||
            dup2(fileno(err.file), STDERR_FILENO) < 0 || chdir(script.parent_path().c_str()) != 0) _exit(126);
        execlp(python.c_str(), python.c_str(), "-X", "utf8", script.c_str(), static_cast<char*>(nullptr));
        perror("無法啟動執行檔");
        _exit(127);
    }
    int status = 0;
    for (;;) {
        pid_t waited = waitpid(pid, &status, WNOHANG);
        if (waited == pid) break;
        if (waited < 0 && errno != EINTR) throw std::runtime_error("無法等待子程序");
        if (std::chrono::duration<double>(Clock::now() - start).count() >= timeout) {
            result.timeout = true;
            kill(pid, SIGKILL);
            while (waitpid(pid, &status, 0) < 0 && errno == EINTR) {}
            break;
        }
        std::this_thread::sleep_for(std::chrono::milliseconds(10));
    }
    if (!result.timeout) result.code = WIFEXITED(status) ? WEXITSTATUS(status) : -WTERMSIG(status);
#endif
    result.elapsed = std::chrono::duration<double>(Clock::now() - start).count();
    result.out = out.read(); result.err = err.read();
    return result;
}

void print_output(const std::string& title, const std::string& text) {
    std::cout << "--- " << title << " ---\n";
    if (text.empty()) { std::cout << "（空）\n"; return; }
    // 無效位元組以替代字元顯示；比對前仍對原始輸出做嚴格 UTF-8 驗證。
    for (size_t i = 0; i < text.size();) {
        size_t n = 1;
        unsigned char c = text[i];
        if (c >= 0xc2 && c <= 0xdf) n = 2;
        else if (c >= 0xe0 && c <= 0xef) n = 3;
        else if (c >= 0xf0 && c <= 0xf4) n = 4;
        std::string piece = text.substr(i, n);
        if (valid_utf8(piece)) { std::cout << piece; i += n; }
        else { std::cout << "\xef\xbf\xbd"; ++i; }
    }
    if (text.back() != '\n') std::cout << '\n';
}

fs::path executable_path(const char* argv0) {
#ifdef _WIN32
    (void)argv0;
    std::vector<wchar_t> buffer(32768);
    DWORD n = GetModuleFileNameW(nullptr, buffer.data(), static_cast<DWORD>(buffer.size()));
    if (!n || n == buffer.size()) throw std::runtime_error("無法取得執行檔路徑");
    return fs::path(std::wstring(buffer.data(), n));
#else
    std::error_code error;
    auto path = fs::read_symlink("/proc/self/exe", error);
    if (!error) return path;
    return fs::canonical(argv0);
#endif
}

int main(int argc, char** argv) {
#ifdef _WIN32
    SetConsoleOutputCP(CP_UTF8);
    // Windows 的窄字元 argv 可能無法表示中文路徑，從原始 Unicode 命令列轉為 UTF-8。
    int wide_count = 0;
    wchar_t** wide_args = CommandLineToArgvW(GetCommandLineW(), &wide_count);
    if (!wide_args) { std::cerr << "無法讀取命令列\n"; return 2; }
    std::vector<std::string> arguments;
    for (int i = 0; i < wide_count; ++i) {
        int n = WideCharToMultiByte(CP_UTF8, 0, wide_args[i], -1, nullptr, 0, nullptr, nullptr);
        std::string value(n, '\0');
        WideCharToMultiByte(CP_UTF8, 0, wide_args[i], -1, value.data(), n, nullptr, nullptr);
        value.pop_back();
        arguments.push_back(value);
    }
    LocalFree(wide_args);
    std::vector<char*> argument_pointers;
    for (auto& argument : arguments) argument_pointers.push_back(argument.data());
    argc = wide_count;
    argv = argument_pointers.data();
#endif
    std::string input_path, expected_path;
#ifdef _WIN32
    std::string python = "python";
#else
    std::string python = "python3";
#endif
    double timeout = 5;
    std::string input, expected;
    fs::path script;
    try {
        for (int i = 1; i < argc; ++i) {
            std::string option = argv[i];
            if (option == "--help" || option == "-h") {
                std::cout << "validator --input FILE --expected FILE [--timeout SECONDS] [--python EXECUTABLE]\n"
                             "執行同目錄的 hello.py；預設時間上限為 5 秒。\n";
                return 0;
            }
            auto equal = option.find('=');
            std::string value;
            if (equal != std::string::npos) { value = option.substr(equal + 1); option.resize(equal); }
            else if (i + 1 < argc) value = argv[++i];
            else throw std::runtime_error("缺少參數值：" + option);
            if (option == "--input") input_path = value;
            else if (option == "--expected") expected_path = value;
            else if (option == "--python") python = value;
            else if (option == "--timeout") {
                size_t used = 0;
                try { timeout = std::stod(value, &used); }
                catch (...) { throw std::runtime_error("時間上限必須是大於 0 的有限秒數"); }
                if (used != value.size() || !std::isfinite(timeout) || timeout <= 0)
                    throw std::runtime_error("時間上限必須是大於 0 的有限秒數");
            } else throw std::runtime_error("未知參數：" + option);
        }
        if (input_path.empty() || expected_path.empty()) throw std::runtime_error("必須指定 --input 與 --expected");
        // 含目錄的 Python 路徑須在切換子程序工作目錄前解析。
        if (fs::u8path(python).has_parent_path()) python = fs::absolute(fs::u8path(python)).u8string();
        script = executable_path(argv[0]).parent_path() / "hello.py";
        if (!fs::is_regular_file(script)) throw std::runtime_error("找不到要驗證的 hello.py：" + script.u8string());
        input = read_test_file(expand_home(input_path));
        expected = read_test_file(expand_home(expected_path));
    } catch (const std::exception& error) {
        std::cerr << "error: " << error.what() << '\n'; return 2;
    }
    try {
        Result result = run(script, python, input, timeout);
        auto actual = normalize_output(result.out), answer = normalize_output(expected);
        bool passed = !result.timeout && result.code == 0 && valid_utf8(result.out) && actual == answer;
        std::string message;
        if (result.timeout) message = "執行逾時，已停止執行程式。";
        else if (result.code != 0) message = "執行失敗：結束代碼 " + std::to_string(result.code);
        else if (!valid_utf8(result.out)) message = "無法比較：程式輸出不是有效的 UTF-8 文字。";
        else if (passed) message = "通過：實際輸出與預期輸出相符。";
        else {
            size_t i = 0, line = 1;
            while (i < actual.size() && i < answer.size() && actual[i] == answer[i]) {
                if (actual[i++] == '\n') ++line;
            }
            // 一邊缺少行時，差異位於新增的下一行。
            if ((i == actual.size() && i < answer.size() && answer[i] == '\n') ||
                (i == answer.size() && i < actual.size() && actual[i] == '\n')) ++line;
            message = "未通過：第 " + std::to_string(line) + " 行不同（包含空白差異）。";
        }
        std::cout << (passed ? "PASS：" : "FAIL：") << message << '\n'
                  << "耗時：" << std::fixed << std::setprecision(3) << result.elapsed << " 秒；程式結束代碼："
                  << (result.timeout ? "無" : std::to_string(result.code)) << '\n';
        print_output("實際輸出（stdout）", result.out);
        if (!passed) print_output("預期輸出", expected);
        if (!result.err.empty()) print_output("程式錯誤訊息（stderr）", result.err);
        return passed ? 0 : 1;
    } catch (const std::exception& error) {
        std::cout << "FAIL：無法啟動或執行程式：" << error.what() << '\n'; return 1;
    }
}
