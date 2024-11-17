import inspect


def determine_function_type(func):
    if isinstance(func, classmethod):
        # Decorated function is a class method
        def wrapper(cls, *args, **kwargs):
            print("Start CLASS method: ", func.__name__)
            cls_ = func.__get__(None, cls)(*args, **kwargs)
            print("End CLASS method\n\n")
            return cls_
        return classmethod(wrapper)
    elif isinstance(func, staticmethod):
        # Decorated function is a static method
        def wrapper(*args, **kwargs):
            print("Start STATIC method: ", func.__name__)
            func1 = func(*args, **kwargs)
            print("End STATIC method\n\n")
            return func1
        return staticmethod(wrapper)
    else:
        try:
            def wrapper(self, *args, **kwargs):
                print("Start INSTANCE method: ", func.__name__)
                # func1 = func.__get__(None, self)(self, *args, **kwargs)
                func1 = func(*args, **kwargs)
                print("End INSTANCE method\n\n")
                return func1
            return wrapper
        except TypeError:
            # Decorated function is an instance method
            def wrapper(*args, **kwargs):
                print("Start STANDALONE FUNCTION: ", func.__name__)
                func1 = func(*args, **kwargs)
                print("End STANDALONE FUNCTION\n\n")
                return func1
            return wrapper


class MyClass:
    def __init__(self):
        self.value = 42

    @determine_function_type
    @classmethod
    def my_class_method(cls):
        print("Inside CLASS method")

    @determine_function_type
    @staticmethod
    def my_static_method():
        print("Inside STATIC method")

    @determine_function_type
    def my_instance_method(self):
        print("Inside INSTANCE method. Value =", self.value)


@determine_function_type
def my_function():
    print("Inside STANDALONE function")


# Usage examples
my_instance = MyClass()
# my_instance.my_class_method()  # Output: Decorated class method: my_method \n Inside class method
# MyClass.my_class_method()  # Output: Decorated class method: my_method \n Inside class method
# MyClass.my_static_method()  # Output: Decorated static method: my_static_method \n Inside static method
# my_instance.my_instance_method()  # Output: Decorated instance method: my_instance_method \n Inside instance method. Value = 42
my_function()  # Output: Decorated function: my_function \n Inside standalone function

