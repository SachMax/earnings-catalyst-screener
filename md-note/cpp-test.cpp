# include <iostream> // a header file that contains input and output functions

/*this is for multi-line comment*/

int main () {
    std::string name;
    
    std::cout << "what's your name? ";
    std::cin >> name;
    std::cout << "hi " << name;
    return 0;
}