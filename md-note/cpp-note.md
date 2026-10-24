# C++ NOTE 

## Basic Stuff
### I/O operations
```cpp
# include <iostream> // a header file that contains input and output functions

/*this is for multi-line comment*/

int main () {
    std::string name;
    std::string full_name;
    
    std::cout << "what's your name? ";
    std::cin >> name; //without space
    std::cout << "hi " << name;
    std::cout << "\n\n";

    std::cout << "what's your full name? ";
    std::getline(std::cin >> std::ws, full_name); // with space, '>> std::ws' is required
    std::cout << "hi " << full_name;
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

### typedef & using
```cpp
# include <iostream>

typedef std::string str;
using num = int; // you can also use 'using' instead of typedef

int main () {
    str name="max"; // instead of using std::string, you can use 'str' to declare string var
    num x = 1;
    std::cout << "nihao " << name;
    std::cout << x;
    return 0;
}
```

### type conversion
```cpp
# include <iostream>

typedef std::string str;
using num = int;

int main () {
    double pi=3.14;
    pi = (int) pi;
    num x = 1;
    std::cout << "nihao " << pi << "\n";
    std::cout << x;
    return 0;
}
// output:
// nihao 3
// 1
```

### math operations
```cpp
# include <iostream> 
#include <cmath>


int main () {
    double x=2.6;
    double y=4.5;
    double z;
    // z = std::max(x,y); //= 4.5
    // z = std::min(x,y); //= 2.5
    z = pow(2,3); //= 8
    z = sqrt(9); //= 3
    z = abs(-3); //= 3
    z = round(x); //= 3
    z = ceil(x); // round up = 3
    z = floor(x); // round down = 2

    std::cout << z;
    return 0;
}
```

## CONDITIONS
### IF/ELSE
```cpp
# include <iostream> 

int main () {
    int age;
    std::cout << "what's your age? ";
    std::cin >> age;

    if (age < 18 & age >= 0) {
        std::cout << "you are a minor";
    }
    else if (age < 0) {
        std::cout << "you haven't been borned yet";
    }
    else {
        std::cout << "you are not a minor";
    }
    return 0;
}
```

### switches
```cpp
# include <iostream> 

int main () {
    int age;
    std::cout << "what's your age? ";
    std::cin >> age;

    switch(age<18){
        case 0:
            std::cout << "you are not a minor";
            break;
        case 1:
            std::cout << "you are a minor";
            break;
        default:
            std::cout << "unknown";
            break;
    }

}
```

### ternary operator `?`
```cpp
# include <iostream> 

int main () {
    int age;
    std::cout << "what's your age? ";
    std::cin >> age;

    // condition ? true: false
    age < 18 ? std::cout << "you are a minor": std::cout << "you are not a minor";
}
```

### logical operators 
- `&&`: this is basically `and` in python
- `||`: this is an 'or'
- `!`: this is a 'not' operator

## Useful string methods
- `.empty()`: check whether its empty or not
- `.length()`: basically len() in python
- `.clear()`: to clear the string -> ""
- `.append()`: add another string at the end 
- `.at()`: accepts integer, for ex=0 -> return the first letter of the string
- `.insert(#index, #string)`: to insert string in certaiin index
- `.find()`: to find certain string in a string
- `.erase(0, 3)`: to erase a string based on the range of the given index -> in the eg.:index 0, 1, 2 are erased

## LOOPS
### while loop
```cpp
//basically, its the same with python but the syntax is different
# include <iostream> 

int main () {
    bool run=true;
    int i=1;
    while (run) {
        if (i > 10) {
            run=false;
            break;
        }
        std::cout << (i);
        i++;
    }
}

```

### do while loops
```cpp
# include <iostream> 

int main () {
    int guess;
    do {
        std::cout << "guess the number from 1-5: ";
        std::cin >> guess;
    }
    while (guess!=4);
    
    std::cout << "you guessed it right!";

    return 0;
}
```

### for loop
```cpp
# include <iostream> 

int main () {
    
    for (int i=0; i < 10; i++) {
        std::cout << i << "\n";
    }

    return 0;
}
```

### foreach loop
```cpp
# include <iostream> 

int main () {
    
    std::string grade[5] = {"A", "B", "C", "D", "F"};

    for (std::string i : grade ) {
        std::cout << i << "\n";
    }

    return 0;
}
```

## arrays
```cpp
# include <iostream> 

int main () {
    
    int numbers[4] = {1, 2, 3, 4};

    std::cout << numbers << "\n";
    std::cout << numbers[0] << "\n";
    std::cout << numbers[2];

    return 0;
}

/*
output:
0x6d349ff910
1
3
*/
```

## fill method 
```cpp
#include <iostream> 

int main () {
    
    int size = 10;
    std::string greet[size];

    std::fill(greet, greet + size, "hi");
    for (std::string i : greet) {
        std::cout << i << "\n";
    }
    return 0;
}
```

## memory addr & pointers
### memory address
```cpp
#include <iostream> 

int main () {
    
    int size = 10;
    std::string greet = "hi";
    double num = 4.50;

    std::cout << &size;
    std::cout << &greet;
    std::cout << &num;
    return 0;

/*
output:
0x6b0a5ffb20
0x6b0a5ffb00
0x6b0a5ffaf8
*/
}
```
### pass by reference (memory  address)
```cpp
#include <iostream> 

std::string swap(std::string &x, std::string &y) {
    std::string temp;
    temp = x;
    x = y;
    y = temp;
    return x, y;
}

int main () {
    std::string x = "max";
    std::string y = "nick";
    x, y = swap(x, y);
    std::cout << "x: " << x << "\n";
    std::cout << "y: " << y;
    return 0;
}
```

### pointers
```cpp
#include <iostream> 

int main () {
    std::string x = "max";
    std::string *pX = &x;

    int numbers [5] = {1, 2, 3, 4, 5};
    int *pNumbers = numbers;

    std::cout << *(pNumbers + 1) << "\n";
    std::cout << *(pNumbers + 3) << "\n";
    std::cout << *pX << "\n";
    return 0;
}
```

### null pointers
```cpp
#include <iostream> 

int main () {
    int *pointer = nullptr;
    int x = 123;

    pointer = &x;

    if (pointer == nullptr) {
        std::cout << "pointer was not assigned";
    }
    else {
        std::cout << "pointer was assigned" << "\n";
        std::cout << *pointer;
    }
    return 0;
}
```

## Dynamic memory
```cpp
#include <iostream> 

int *temporary_global_var = nullptr;

void openLargeFile () {
    temporary_global_var = new int(123);
    std::cout << "successfully taken a chunk of RAM" << "\n";
}

void modifying_data () {
    (*temporary_global_var)++; // based on the operator precedence, '++' is ranked higher than a pointer -> hence () is needed
    std::cout << "successfully +1" << "\n";
}

int main () {
    openLargeFile();
    if (temporary_global_var == nullptr) {
        std::cout << "pointer was not assigned";
    }
    else {
        std::cout << "pointer was assigned" << "\n";
        std::cout << *temporary_global_var << "\n";

        modifying_data();

        std::cout << *temporary_global_var;
    }
    delete temporary_global_var; // clear the RAM
    temporary_global_var = nullptr; // <--- Clear the key!

    return 0;

/*
successfully taken a chunk of RAM
pointer was assigned
123
successfully +1
124
*/
}
```
so basically, a dynamic memory is like taking a chunk of your ram and declaring it using a pointer (to access the memory address), storing it on the heap. this way, the data would not be vanished until the heap object is deleted. therefore, you can use this as a temporary global variable. this method is highly flexible and usually for arrays with unknown size or a data that is too large (~50MB or 1 GB). Using standard memory would crash and result stack overflow error due to the stack size limit. Thats why a better approach is to use the heap.

## Recursion
```cpp
#include <iostream> 

int factorial (int number) {
    if (number > 1) {
        return number * factorial(number - 1);
    }
    else {
        return 1;
    }
}

int main () {

    int factor = factorial(4);
    std::cout << factor;
    return 0;
}
```

## Function Template
```cpp
#include <iostream> 

// for similar function with different datatypes
template <typename T, typename U>

auto max (T x, U y) {
    return (x > y) ? x : y;
}

int main () {

    double x = 2.1;
    int y = 3;

    std::cout << max(x, y);;
    return 0;
}
```

## struct
works like class in python
```cpp
#include <iostream> 

struct student {
    std::string name;
    double gpa;
};

int main () {

    student student1;
    student1.name = "Max";
    student1.gpa = 4.0;

    student student2;
    student2.name = "Nick";
    student2.gpa = 2.1;

    std::cout << student1.name << "\n";
    std::cout << student1.gpa << "\n\n";

    std::cout << student2.name << "\n";
    std::cout << student2.gpa;
    return 0;
}
```

## enums 
user-defined data type that consists of paired named-integers constants
```cpp
#include <iostream> 

enum guidance {lower = 0, reaffirm = 1, raised = 2};

int main () {
    guidance report = lower;
    switch (report) {
        case lower: std::cout << "skip"; break;
        case reaffirm: std::cout << "buy half"; break;
        case raised: std::cout << "buy"; break;
    }

    return 0;
}
```

## Object Oriented Programming
object is basically just class in python. 

```cpp
#include <iostream> 

class market_option {
    public: //classes are 'private:' by default, therefore you need 'pblic:' to make it accessible for the main func
        std::string ticker;
        int shares;
        std::string method;

        void buy (std::string ticker, int shares, std::string method) {
            std::cout << "you bought " << ticker << " for " << shares << "shares using " << method << "\n"; 
        }

        void sell (std::string ticker, int shares, std::string method) {
            std::cout << "you sold " << ticker << " for " << shares << "shares using " << method << "\n"; 
        }
};

int main () {

    market_option day1;

    day1.ticker = "NVDA";
    day1.shares = 10;
    day1.method = "limit";
    
    std::cout << day1.ticker << "\t" << day1.shares << "\t" << day1.method << "\n";
    day1.buy(day1.ticker, day1.shares, day1.method);
    day1.sell(day1.ticker, day1.shares, day1.method);
    return 0;
}

/*
NVDA    10      limit
you bought NVDA for 10shares using limit
you sold NVDA for 10shares using limit
*/
```

### Constructor & Destructor
just an easier way to assign values to the object attributes and prevent memory leak
```cpp
#include <iostream>

class market_option {
    public: //classes are 'private:' by default, therefore you need 'pblic:' to make it accessible for the main func
        std::string ticker;
        int shares;
        std::string method;

        // constructor
        market_option (std::string ticker, int shares, std::string method) {
            std::cout << "created class obj" << "\n";

            this->ticker = ticker; // similar to python, self.ticker = ticker
            this->shares = shares;
            this->method = method;
        }

        /*
        // this also works but its less readable
        market_option (std::string x, int y, std::string z) {
            ticker = x;
            shares = y;
            method = z;
        }
        */

        // destructor
        ~market_option() {
            std::cout << "destroyed class obj" << "\n";
        }


        void buy (std::string ticker, int shares, std::string method) {
            std::cout << "you bought " << ticker << " for " << shares << "shares using " << method << "\n"; 
        }

        void sell (std::string ticker, int shares, std::string method) {
            std::cout << "you sold " << ticker << " for " << shares << "shares using " << method << "\n"; 
        }
};

void func(){
    market_option day1("NVDA", 10, "limit");
    
    std::cout << day1.ticker << "\t" << day1.shares << "\t" << day1.method << "\n";
    day1.buy(day1.ticker, day1.shares, day1.method);
    day1.sell(day1.ticker, day1.shares, day1.method);
}

int main () {

    func();
    return 0;
}

/* output:
created class obj
NVDA    10      limit
you bought NVDA for 10shares using limit
you sold NVDA for 10shares using limit
destroyed class obj
*/
```

## inheritance
```cpp
#include <iostream> 

class tech_stock {
    public:
        bool AI_related = true;
    
    void buy(){
        std::cout << "im buying this tech stock";
    }
    void sell(){
    std::cout << "im selling this tech stock";
    }
    
};

class AAPL : public tech_stock {
    public:
        bool AI_related = false;
    
        void owner() {
            std::cout << "tim cook" << "\n";
        }
};

class NVDA : public tech_stock {
    public:
        void owner() {
            std::cout << "jenson huang" << "\n";
        }
};

int main() {
    AAPL aapl;
    NVDA nvda;
    aapl.owner();
    std::cout << aapl.AI_related << "\n";

    nvda.owner();
    std::cout << nvda.AI_related;
    
    return 0;
}

/*
output:
tim cook
0
jenson huang
1
*/
```

## `std::vector`
```cpp
#include <iostream>
#include <vector>

struct Trade {
    std::string ticker;
    double price;
    int shares;
};

int main () 
{
    std::vector<Trade> trades;
    Trade trade1{"NVDA", 180.50, 10};
    trades.push_back(trade1);

    std::vector<double> prices = {
        100.0,
        102.0,
        99.0
    };

    prices.push_back(105.4); // append value '105.0' to prices
    prices.push_back(107.7);

    std::cout << prices.size() << "\t";
    std::cout << prices.at(3) << "\n";

    std::cout << trades.at(0).ticker;

    return 0;
}
```

STACK                                HEAP (Dynamic Memory)
+-------------------------+          +-------+-------+-------+-------+-------+

| prices (vector object)  |          | 100.0 | 102.0 |  99.0 | 105.0 | 107.0 |
|  - Start pointer  --------------> |[idx 0]|[idx 1]|[idx 2]|[idx 3]|[idx 4]|
|  - Size pointer         |          +-------+-------+-------+-------+-------+
|  - Capacity pointer     |          | Free space allocated for growth...    |
+-------------------------+          +---------------------------------------+

When you call prices.push_back(105.0), you do not manually call new. The vector automatically requests a chunk of dynamic heap memory for you behind the scenes.

## optimizing `std::vector`
```cpp
#include <iostream>
#include <vector>
#include <string>

struct Trade {
    std::string symbol;
    double price;
    int quantity;
};

int main() {
    // -------------------------------------------------------------
    // 1. DEMONSTRATING SIZE VS CAPACITY & REALLOCATION
    // -------------------------------------------------------------
    std::vector<Trade> trades;

    std::cout << "--- Initial State ---\n";
    std::cout << "Size: " << trades.size() << ", Capacity: " << trades.capacity() << "\n\n";

    std::cout << "--- Adding 5 items without reserving ---\n";
    for (int i = 1; i <= 5; ++i) {
        trades.push_back({"AAPL", 150.0 + i, 100});
        std::cout << "Added item " << i 
                  << " -> Size: " << trades.size() 
                  << ", Capacity: " << trades.capacity() << "\n";
    }
    // Notice how capacity jumps (e.g., 1 -> 2 -> 4 -> 8) as it reallocates!

    // -------------------------------------------------------------
    // 2. DEMONSTRATING REFERENCE INVALIDATION (THE DANGER)
    // -------------------------------------------------------------
    std::cout << "\n--- Reference Invalidation Danger ---\n";
    
    // Grab a reference to the very first item in the current memory block
    Trade& first_trade = trades[0];
    std::cout << "Before reallocation, first trade price: $" << first_trade.price << "\n";
    std::cout << "Memory address of trades[0]: " << &trades[0] << "\n";

    // Force a reallocation by pushing items until capacity is exceeded
    // Our current capacity is 8 (or similar), filling it up forces a move.
    while (trades.size() < 10) {
        trades.push_back({"GOOG", 2500.0, 50});
    }

    std::cout << "\nAfter filling up past original capacity:\n";
    std::cout << "New Size: " << trades.size() << ", New Capacity: " << trades.capacity() << "\n";
    std::cout << "New memory address of trades[0]: " << &trades[0] << "\n";

    // CRITICAL WARNING: 'first_trade' is now pointing to the OLD, destroyed memory address.
    // Reading 'first_trade.price' here is Undefined Behavior! It might crash or print garbage.
    // std::cout << first_trade.price; // DO NOT DO THIS

    // -------------------------------------------------------------
    // 3. OPTIMIZING WITH reserve()
    // -------------------------------------------------------------
    std::cout << "\n--- Optimizing with reserve() ---\n";
    std::vector<Trade> optimized_trades;
    
    // Allocate space for 10,000 items upfront in ONE system call
    optimized_trades.reserve(10000); 
    
    std::cout << "After reserve(10000) -> Size: " << optimized_trades.size() 
              << ", Capacity: " << optimized_trades.capacity() << "\n";

    // This loop runs blazing fast because zero reallocations happen
    for (int i = 0; i < 5; ++i) {
        optimized_trades.push_back({"MSFT", 300.0, 200});
    }
    
    std::cout << "After adding 5 items   -> Size: " << optimized_trades.size() 
              << ", Capacity: " << optimized_trades.capacity() << "\n";

    return 0;
}

/* output:
--- Initial State ---
Size: 0, Capacity: 0

--- Adding 5 items without reserving ---
Added item 1 -> Size: 1, Capacity: 1
Added item 2 -> Size: 2, Capacity: 2
Added item 3 -> Size: 3, Capacity: 4
Added item 4 -> Size: 4, Capacity: 4
Added item 5 -> Size: 5, Capacity: 8

--- Reference Invalidation Danger ---
Before reallocation, first trade price: $151
Memory address of trades[0]: 0x17461d47170

After filling up past original capacity:
New Size: 10, New Capacity: 16
New memory address of trades[0]: 0x17461d60160

--- Optimizing with reserve() ---
After reserve(10000) -> Size: 0, Capacity: 10000
After adding 5 items   -> Size: 5, Capacity: 10000
*/
```

## const
```cpp
#include <iostream>
#include <vector>
#include <string>

class Portfolio {
public:
    double cash() const { 
        return cash_; 
    }
    
    void set_cash(double amount) { 
        cash_ = amount; 
    }

private:
    double cash_ = 100.5;
};

// pass a reference. therefore the compiler doesnt copy the argument
void print_signal(const Portfolio& signal) {
    // LEGAL: .cash() is a const method, so we can call it on a const reference
    std::cout << "Inside function: " << signal.cash() << "\n"; 
    
    // ILLEGAL (uncommenting this will break compilation):
    // signal.set_cash(20.1); 
}

int main() {
    const int num = 5;
    
    Portfolio my_port;
    std::cout << "Initial cash: " << my_port.cash() << "\n";
    
    my_port.set_cash(30.9); // Legal: my_port is not a const variable here
    std::cout << "Updated cash: " << my_port.cash() << "\n";
    
    std::cout << "Const num: " << num << "\n";
    
    // ILLEGAL (uncommenting this will break compilation):
    // num = 7; 
    
    print_signal(my_port);
    return 0;
}
```

## Member Initializer Lists
```cpp
#include <iostream>
#include <string>

class OrderBook {
public:
    OrderBook() { std::cout << "  [Slow] Empty Book Created\n"; }
    OrderBook(std::string symbol) { std::cout << "  [Fast] Book Built directly for " << symbol << "\n"; }
    OrderBook& operator=(const OrderBook& other) { std::cout << "  [Slow] Book Overwritten\n"; return *this; }
};

// --- APPROACH 1: UNOPTIMIZED (Creates empty, then overwrites) ---
class UnoptimizedStrategy {
    OrderBook book; // Built empty automatically before curly brace opens
public:
    UnoptimizedStrategy(std::string ticker) {
        book = OrderBook(ticker); // Creates temporary book and overwrites the empty one
    }
};

// --- APPROACH 2: OPTIMIZED (Builds directly) ---
class OptimizedStrategy {
    OrderBook book;
public:
    OptimizedStrategy(std::string ticker) : book(ticker) {} // Direct initialization
};

int main() {
    std::cout << "=== Testing Unoptimized Strategy ===\n";
    UnoptimizedStrategy s1("AAPL");

    std::cout << "\n=== Testing Optimized Strategy ===\n";
    OptimizedStrategy s2("TSLA");

    return 0;
}

```

## Copying and copy constructors

### The Bad Practice
```cpp
#include <iostream>
#include <string>

// ============================================================================
// 1. GOOD PRACTICE: The Rule of Zero (Safe and Automatic)
// ============================================================================
class SafePosition {
public:
    std::string ticker;
    int shares;
    
    // No copy constructor written! C++ auto-generates a safe one.
    SafePosition(std::string t, int s) : ticker(t), shares(s) {}
};

// ============================================================================
// 2. BAD PRACTICE: Raw Pointer without Custom Copying (Causes Crash)
// ============================================================================
class DangerousPosition {
public:
    std::string ticker;
    int* shares; // Raw pointer to heap memory

    DangerousPosition(std::string t, int s) {
        ticker = t;
        shares = new int(s); // Allocate heap memory
    }

    ~DangerousPosition() {
        std::cout << "Cleaning up memory for " << ticker << "\n";
        delete shares; // Free heap memory
    }
};

int main() {
    std::cout << "=== Running Safe Rule of Zero ===\n";
    SafePosition safe_a("NVDA", 10);
    SafePosition safe_b = safe_a; // Calls auto-generated copy constructor
    
    safe_b.shares = 20; // Changing b does NOT affect a
    std::cout << "safe_a shares: " << safe_a.shares << "\n"; // Prints 10
    std::cout << "safe_b shares: " << safe_b.shares << "\n"; // Prints 20


    std::cout << "\n=== Running Dangerous Raw Pointer Copy ===\n";
    {
        DangerousPosition dang_a("AAPL", 50);
        DangerousPosition dang_b = dang_a; // WARNING: Shallow copies the POINTER address!
        
        std::cout << "dang_a shares pointer address: " << dang_a.shares << "\n";
        std::cout << "dang_b shares pointer address: " << dang_b.shares << "\n"; 
        // Both point to the exact same memory location!
        
    } // <-- Braces end here, so both objects go out of scope and trigger their destructors.
    
    // CRASH WARNING: 
    // dang_b destructor runs first and deletes the memory.
    // dang_a destructor runs next and tries to delete the SAME memory. 
    // This causes a catastrophic "Double Free" crash!

    return 0;
}
```
> The Rule of Zero: If your class does not manually manage raw hardware resources (like raw pointers using new/delete, open database connections, or file handles), you should never write a custom destructor, copy constructor, or copy assignment operator. You should let the compiler auto-generate all of them.

### The solution
```cpp
#include <iostream>
#include <string>

class FixedPosition {
public:
    std::string ticker;
    int* shares; // Raw pointer to heap memory

    // Standard Constructor
    FixedPosition(std::string t, int s) {
        ticker = t;
        shares = new int(s); 
    }

    // --- CUSTOM COPY CONSTRUCTOR (The Deep Copy) ---
    FixedPosition(const FixedPosition& other) {
        ticker = other.ticker; // Copies the string safely
        
        // Instead of copying the address, allocate BRAND NEW memory
        // and copy the actual value stored inside 'other.shares'
        shares = new int(*other.shares); 
        
        std::cout << "  [Deep Copy] Allocated new memory for " << ticker << "\n";
    }

    // Destructor (Now perfectly safe)
    ~FixedPosition() {
        std::cout << "  [Destructor] Cleaning up memory for " << ticker << "\n";
        delete shares; 
    }
};

int main() {
    std::cout << "=== Running Fixed Pointer Copy ===\n";
    {
        FixedPosition pos_a("AAPL", 50);
        FixedPosition pos_b = pos_a; // Invokes our custom deep copy constructor

        std::cout << "pos_a pointer address: " << pos_a.shares << " (Value: " << *pos_a.shares << ")\n";
        std::cout << "pos_b pointer address: " << pos_b.shares << " (Value: " << *pos_b.shares << ")\n";
        // Notice the addresses are completely different!

        // Changing B now has absolutely zero effect on A
        *pos_b.shares = 99;
        std::cout << "pos_a value after change: " << *pos_a.shares << "\n"; // Stays 50
        std::cout << "pos_b value after change: " << *pos_b.shares << "\n"; // Becomes 99

    } // Braces end: both destructors execute smoothly without crashing.
    
    std::cout << "=== Success! No Double Free Crash ===\n";
    return 0;
}
```

## auto
In C++, the auto keyword activates automatic type deduction. It tells the compiler: "You already know the type of the value on the right side of the equals sign, so figure it out for me."

## lambdas
same like python, a nameless function 

in python: `lambda x: x * 2`
in c++: `[] (double x) { return x * 2; }`

```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm> // Required for std::sort

struct Signal {
    std::string ticker;
    double score;
};

// Helper function to cleanly print our vector of signals
void print_signals(const std::vector<Signal>& signals) {
    for (const auto& s : signals) {
        std::cout << "  [" << s.ticker << "] Score: " << s.score << "\n";
    }
}

int main() {
    std::vector<Signal> signals = {
        {"NVDA", 85.5},
        {"AAPL", 92.1},
        {"TSLA", 64.3},
        {"MSFT", 78.9}
    };

    std::cout << "=== Original Order ===\n";
    print_signals(signals);

    // -------------------------------------------------------------
    // 1. SORT BY SCORE (HIGHEST FIRST)
    // -------------------------------------------------------------
    // Your lambda returns true if 'a' has a bigger score than 'b'
    std::sort(signals.begin(), signals.end(), [](const Signal& a, const Signal& b) {
        return a.score > b.score; 
    });

    std::cout << "\n=== Sorted by Score (Highest First) ===\n";
    print_signals(signals);

    // -------------------------------------------------------------
    // 2. SORT ALPHABETICALLY BY TICKER (A TO Z)
    // -------------------------------------------------------------
    // Your lambda returns true if string 'a.ticker' comes before 'b.ticker'
    std::sort(signals.begin(), signals.end(), [](const Signal& a, const Signal& b) {
        return a.ticker < b.ticker; 
    });

    std::cout << "\n=== Sorted Alphabetically by Ticker (A-Z) ===\n";
    print_signals(signals);

    return 0;
}
```

## sorting
```cpp
#include <iostream>
#include <vector>
#include <string>
#include <algorithm> // Required for std::sort

struct Signal {
    std::string ticker;
    double score;
};

int main() {
    // 1. Create a list of unsorted candidate trades
    std::vector<Signal> signals = {
        {"AMD",  0.82},
        {"AAPL", 0.74},
        {"NVDA", 0.91},
        {"MSFT", 0.65}
    };

    std::cout << "=== Unsorted Strategy Candidates ===\n";
    for (const auto& s : signals) {
        std::cout << s.ticker << "\t" << s.score << "\n";
    }

    // 2. Sort descending (highest score first) to rank the trades
    std::sort(
        signals.begin(),
        signals.end(),
        [](const Signal& a, const Signal& b) {
            return a.score > b.score; 
        }
    );

    // 3. Print out the ranked trades
    std::cout << "\n=== Ranked Candidate Trades ===\n";
    for (const auto& s : signals) {
        // Using \t adds a clean tab column space between ticker and score
        std::cout << s.ticker << "\t" << s.score << "\n";
    }

    return 0;
}

/* output:
=== Unsorted Strategy Candidates ===
AMD     0.82
AAPL    0.74
NVDA    0.91
MSFT    0.65

=== Ranked Candidate Trades ===
NVDA    0.91
AMD     0.82
AAPL    0.74
MSFT    0.65
*/
```

## `std::map` and `std::unordered_map`
this is basically like python's dictionary but with different syntax. 
`std::unordered_map<std::string, int> positions;`, inside the <> = those are key and value type, but c++ stores them as std::pair. if you want to access the key or the value, you need to use something like ->first or ->second.

```cpp
#include <iostream>
#include <string>
#include <map>
#include <unordered_map>

struct Position {
    int shares;
    double average_price;
};

int main() {
    // -------------------------------------------------------------
    // 1. std::map (Sorted Alphabetically A-Z)
    // -------------------------------------------------------------
    std::map<std::string, int> sorted_positions;
    sorted_positions["NVDA"] = 10;
    sorted_positions["AAPL"] = 5;
    sorted_positions["AMD"]  = 20;
    sorted_positions["TSLA"] = 15;

    std::cout << "=== std::map Output (Always Sorted) ===\n";
    // it->first is the Ticker (Key), it->second is the Shares (Value)
    for (auto it = sorted_positions.begin(); it != sorted_positions.end(); ++it) {
        std::cout << it->first << "\t-> " << it->second << " shares\n";
    }

    // -------------------------------------------------------------
    // 2. std::unordered_map (Hash-based, Random Order, Blazing Fast)
    // -------------------------------------------------------------
    std::unordered_map<std::string, Position> portfolio;
    portfolio["NVDA"] = {100, 125.50};
    portfolio["AAPL"] = {50, 220.00};

    std::cout << "=== Modern Portfolio Loop ===\n";

    // --- STRUCTURED BINDING LOOP --- the modern way
    // [ticker, pos] completely replaces it->first and it->second!
    for (const auto& [ticker, pos] : portfolio) {
        
        // Look how clean this is! No 'first' or 'second' anywhere.
        std::cout << "Ticker: " << ticker << "\n";
        std::cout << "  Shares: " << pos.shares << "\n";
        std::cout << "  Price:  $" << pos.average_price << "\n";
    }

    return 0;
}

/*output:
=== std::map Output (Always Sorted) ===
AAPL    -> 5 shares
AMD     -> 20 shares
NVDA    -> 10 shares
TSLA    -> 15 shares
=== Modern Portfolio Loop ===
Ticker: AAPL
  Shares: 50
  Price:  $220
Ticker: NVDA
  Shares: 100
  Price:  $125.5
*/
```

## Smart pointers
### unique pointer or `std::unique_ptr`
basically, unique pointer is a scope pointer, when the run goes out of scope, the pointer would be deleted. 

### Shared pointer
if you want two pointers to point to the same address, the pointer is destroyed when all of the pointer reached the end of scope.

### Weak pointer
almost the same like shared pointer, but its not pointing to the reference, its just accessing the reference and the value. if the reference  dies, it is invalid and it cannot access it.
```cpp
#include <iostream>
#include <memory> // for smart pointers

class market_option {
    public:

        // constructor
        market_option () {
            std::cout << "created class obj" << "\n";
        }

        // destructor
        ~market_option() {
            std::cout << "destroyed class obj" << "\n";
        }

        void print(){
            std::cout << "print" << "\n";
        }
};

int main () 
{
// the scope
    {
        std::weak_ptr<market_option> weak1;
        {   
            std::shared_ptr<market_option> shared1;
                {
                // first method
                // std::unique_ptr<market_option> Pmarket_option(new market_option);

                // the recommendad way
                std::unique_ptr<market_option> Pmarket_option = std::make_unique<market_option>();
                std::shared_ptr<market_option> Shared_market_option = std::make_shared<market_option>();
                shared1 = Shared_market_option;
                weak1 = Shared_market_option;

                Pmarket_option->print();
                shared1->print();
                Shared_market_option->print();
                
                
            }
            shared1->print();
        }

        /* similar to:
        // 1. Memory allocation and pointer creation
        market_option* Pmarket_option = new market_option();

        Pmarket_option->print();

        // 2. Manual cleanup right before the closing brace
        delete Pmarket_option; 
        */


        // weak1 cannot access shared_market_option pointer again because its already destroyed
    }    
    return 0;
}
```

## Copying values % move semantic
### rvalue (read value)& lvalue (locator value)
okay so basically: 
- lvalues = values that are fixed with a fix memory address, a specific object I can refer to again.
- rvalues = values with temporary memory address, a value/result that I don’t normally need to keep referring to.

how it works is like 
```cpp
int x = 10;
int y = x + 5;
```
10 is an rvalue, it is assigned to x with a fixed address, now the address for the int(10) is gone after x is assigned. after that it also works the same with the following `y = x + 5;`.

### move semantics
now for move semantics, this is for copying huge data usually. instead of copying like y = x, the huge data is going to be moved by treating it as an rvalue. use a return function.

for example:
```cpp
std::vector<double> get_market_data() {
    std::vector<double> temporary_prices = { ...1 million numbers... };
    return temporary_prices; // This returned object is a temporary RVALUE
}

// In your main function:
std::vector<double> my_data = get_market_data();
```
Why we do this? its because copying an rvalue is very fast rather than copying an lvalue.

### `std::move(x)`
finally for std::move, this one is literally the function saying "Treat x as something whose resources are allowed to be moved from."

what if you want to copy an lvalue? 
```cpp
std::vector<double> huge_data = { ...1 million items... };

// This will still trigger a slow COPY because huge_data is an lvalue!
std::vector<double> backup = huge_data; 
```
instead, just do this `std::vector<double> backup = std::move(huge_data);`
therefore, its just like moving ownership, not duplicating them.

however, one critical bug is
```cpp
std::vector<double> other = std::move(data);

// CRITICAL BUG! data has been hollowed out. therefore data wont have access to huge_data, its just empty;
// This will cause a segmentation fault or print absolute garbage!
std::cout << data[0]; 
```

## `<fstream>`
stands for file stream.

streams is basically I/O operations such as `std::cin` (input stream) and `std::cout` (output stream).

a file can also be connected to a stream.
```bash
CSV file
   ↓
std::ifstream
   ↓
your program
```

### `std::ifstream`
stands for input file stream

so,
`std::ifstream file(filepath);` 
means: Create an input stream called file connected to the file at filepath.

for example,
`std::ifstream file("data/sample.csv");`

conceptually,
```bash
data/sample.csv
       │
       ▼
 ┌─────────────┐
 │ ifstream    │
 │    file     │
 └─────────────┘
       │
       ▼
    C++ program
```
Now your program can read information from that file.

### `std::ofstream`
stands for output file stream

so,
`std::ofstream file("output.txt");`
means: allows your program to write to a file.

for example,
```cpp
std::ofstream file("output.txt");

file << "Hello\n";
file << "Trading Engine\n";
```
the resulting file would contain,
Hello
Trading Engine

### checking if file is open
```cpp
std::ifstream file(filepath); //c++ attempts to open the '/file path' then assigned as file

if (!file.is_open()) { // condition: file cannot open
    throw std::runtime_error("Could not open CSV file: " + filepath);
}
```

### reading from a file 
`std::getline(file, line)`
similar to 
`std::getline(std::cin, name);`

suppose a csv file named `"data/close_price.scv"`:
```csv
timestamp,open,high,low,close,volume
2026-09-21,200,205,198,203.5,1500000
2026-09-22,203.5,208,202,207,1800000
```
if you do this,
```cpp
std::string line;

std::getline("data/close_price.csv", line);
// you will get this:
// timestamp,open,high,low,close,volume

```

## `<sstream>`
when you extract lines from a csv file, you get this 
: 2026-09-21,200,205,198,203.5,1500000

you use this library to seperate them

### `std::stringstream`
just write this `std::stringstream ss(line);`

now, you can extract pieces from ss

### Why not use std::getlineagain?
Because the file gives us lines, but the line contains multiple fields.

So we do:
1. Read the line: `std::getline(file, line);`
2. Break the line into fields: `std::stringstream ss(line);`
3. `std::getline(ss, field, ',');`

## tiny example 
```cpp
#include <iostream>
#include <sstream>
#include <string>

int main()
{
    std::string line = "AAPL,200.5,1000";

    std::stringstream ss(line);

    std::string ticker;
    std::string price;
    std::string volume;

    std::getline(ss, ticker, ',');
    std::getline(ss, price, ',');
    std::getline(ss, volume, ',');

    std::cout << ticker << '\n';
    std::cout << price << '\n';
    std::cout << volume << '\n';
}

/*
output:
AAPL
200.5
1000
*/
```

## data type conversion

### string to double
```cpp
std::string field = "203.5";

double price = std::stod(field); 
```

### string to long long
```cpp
std::string field = "1500000";

std::int64_t volume = std::stoll(field);
```

## `std::except` - exceptions

`#include <stdexcept>`

This header provides standard exception classes.

one of the most relevent exceptions: `std::runtime_error`
meaning: "Something went wrong, and normal execution cannot continue."

### throw
```cpp
throw std::runtime_error(
    "Could not open CSV file: " + filepath
);
```
meaning: Stop normal execution here and report this error to whoever is handling exceptions.

### `try` and `catch`
this is very similar to python's `try` and `except`

```cpp
try {
    ...
}
catch (const std::exception& e) {
    std::cerr << "Error: " << e.what() << '\n';
}
```

`std::exception`, is basically like `Exception` in python

`e.what`: returns the error message.

```cpp
throw std::runtime_error("Could not open CSV file");

catch (const std::exception& e) {
    std::cout << e.what();
}

// output: Could not open CSV file
```

