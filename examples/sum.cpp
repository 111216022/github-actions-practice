#include <iostream>

int main() {
    int a, b;
    if (!(std::cin >> a >> b)) {
        std::cerr << "Expected two integers\n";
        return 1;
    }
    std::cout << a + b << '\n';
    return 0;
}
