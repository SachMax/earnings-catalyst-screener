# C++ NOTE 

## Basic Stuff
### I/O operations
```cpp
# include <iostream> // a header file that contains input and output functions

/*this is for multi-line comment*/

int main () {
    int  x = 5;
    double y = 5.67;
    std::string name="max";
    
    std::cout << "hi" << std::endl;
    std::cout << "test" << "\n";
    std::cout << "nihao " << name;
    return 0;
}
```

### Variables 
```cpp
int x = 1;
double y = 2.09;
char letter = "A";
std::string person = "Max";
bool state = true;
const double pi=3.14; // this makes the pi value unchangeable
```

### Namespace
```cpp
# include <iostream>

namespace first {
    std::string name = "nick";
}

namespace second {
    std::string name = "sam";
}

int main () {
    std::string name="max";

    std::cout << "nihao " << first::name << "\n";
    std::cout << "nihao " << name;
    return 0;
}
// output:
// nihao nick
// nihao max
```

### typedef 
```cpp
# include <iostream>

typedef std::string str;

int main () {
    str name="max"; // instead of using std::string, you can use 'str' to declare string var
    std::cout << "nihao " << name;
    return 0;
}
```