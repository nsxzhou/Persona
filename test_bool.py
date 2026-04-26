from pydantic import TypeAdapter
print(TypeAdapter(bool).validate_python("true"))
print(TypeAdapter(bool).validate_python("false"))
