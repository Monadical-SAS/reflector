Now I have gathered comprehensive information about "parse don't validate" principle, Pydantic validators, and branded types. Let me create a thorough report on these topics and how they work together with FastAPI.

# Parse Don't Validate: Best Practices with Pydantic and FastAPI

## Understanding "Parse Don't Validate"

**The "Parse, Don't Validate" principle** is a powerful software design approach that emphasizes transforming data into precise, type-safe structures rather than merely checking data validity and discarding the knowledge gained. This principle, popularized by Alexis King, fundamentally changes how we think about data integrity and type safety.

### Core Concept

The distinction between validation and parsing lies in **information preservation**:

- **Validation**: Checks if data meets certain criteria, returns `()` (unit type), throws away the knowledge gained
- **Parsing**: Transforms data into a more structured type that **encodes the validation result** in the type system

Consider this comparison:

```python
# Validation - throws away knowledge
def validate_non_empty(lst: list) -> None:
    if not lst:
        raise ValueError("List cannot be empty")
    # Knowledge that list is non-empty is lost

# Parsing - preserves knowledge in type system  
def parse_non_empty(lst: list[T]) -> NonEmptyList[T]:
    if not lst:
        raise ValueError("List cannot be empty")
    return NonEmptyList(lst)  # Type guarantees non-emptiness
```

## Pydantic and FastAPI: Natural Parse Don't Validate Implementation

FastAPI with Pydantic provides an excellent foundation for implementing "parse don't validate" patterns automatically. When you define Pydantic models, you're essentially creating parsers that transform raw input data into validated, structured objects.

### Automatic Parsing in FastAPI

FastAPI automatically handles the parsing process for **query parameters**, **path parameters**, and **request bodies**:

```python
from fastapi import FastAPI, Query, Path, Body
from pydantic import BaseModel, Field
from typing import Annotated

app = FastAPI()

class UserRequest(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    email: str = Field(pattern=r'^[^@]+@[^@]+\.[^@]+$')
    age: int = Field(ge=0, le=150)

@app.post("/users/{user_id}")
async def create_user(
    user_id: Annotated[int, Path(gt=0)],  # Path parameter parsing
    active: Annotated[bool, Query()] = True,  # Query parameter parsing  
    user: UserRequest = Body()  # Request body parsing
):
    # At this point, all data is guaranteed to be valid
    # user_id is a positive integer
    # active is a boolean
    # user contains validated name, email, and age
    return {"user_id": user_id, "user": user, "active": active}
```

## Branded Types with Pydantic

**Branded types** (also called "newtypes") create distinct types from primitives that are identical at runtime but different at the type-checking level. This prevents mixing up semantically different values that share the same underlying type.

### Creating Branded Types in Python

```python
from typing import NewType, Annotated
from pydantic import BaseModel, AfterValidator, Field
import re

# Using Python's NewType (static typing only)
UserId = NewType('UserId', int)
EmailAddress = NewType('EmailAddress', str)

# Using Pydantic's Annotated for runtime validation
def validate_user_id(value: int) -> int:
    if value  str:
    if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
        raise ValueError("Invalid email format")
    return value

# Branded types with validation
ValidatedUserId = Annotated[int, AfterValidator(validate_user_id)]
ValidatedEmail = Annotated[str, AfterValidator(validate_email)]
```

### Advanced Branded Types with Custom Classes

For more complex scenarios, create custom classes that inherit from base types:

```python
from typing import Any
from pydantic import BaseModel, Field, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

class EmailAddress(str):
    """Branded email address type with validation."""
    
    @classmethod
    def __get_validators__(cls):
        yield cls.validate
    
    @classmethod
    def validate(cls, value: str) -> 'EmailAddress':
        if not isinstance(value, str):
            raise TypeError('Email must be a string')
        
        if not re.match(r'^[^@]+@[^@]+\.[^@]+$', value):
            raise ValueError('Invalid email format')
            
        return cls(value)
    
    @classmethod
    def __get_pydantic_core_schema__(
        cls, source_type: Any, handler: GetCoreSchemaHandler
    ) -> CoreSchema:
        return core_schema.str_schema(min_length=1, max_length=254)

class StrongPassword(str):
    """Branded password type with strength validation."""
    
    @classmethod
    def validate(cls, value: str) -> 'StrongPassword':
        if len(value)  int:
    if value  int:
        """Calculate offset from page and size."""
        return (self.page - 1) * self.size

@app.get("/items/")
async def get_items(params: Annotated[PaginationParams, Depends()]):
    # params is guaranteed to be valid - no need for further checks
    items = get_items_from_db(
        offset=params.offset,
        limit=params.size,
        order=params.sort_order
    )
    return {"items": items, "pagination": params}
```

### Complex Request Body Parsing

```python
from datetime import datetime, date
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator, model_validator

class OrderItem(BaseModel):
    product_id: ValidatedUserId
    quantity: PositiveInt
    unit_price: Annotated[float, Field(gt=0, description="Price per unit")]
    
    @property
    def total_price(self) -> float:
        return self.quantity * self.unit_price

class DeliveryAddress(BaseModel):
    street: str = Field(min_length=5, max_length=100)
    city: str = Field(min_length=2, max_length=50)
    postal_code: str = Field(pattern=r'^\d{5}(-\d{4})?$')
    country: str = Field(default="US", min_length=2, max_length=2)

class OrderRequest(BaseModel):
    customer_email: EmailAddress
    items: List[OrderItem] = Field(min_length=1, description="At least one item required")
    delivery_address: DeliveryAddress
    delivery_date: Optional[date] = None
    
    @field_validator('delivery_date')
    @classmethod
    def validate_delivery_date(cls, value: Optional[date]) -> Optional[date]:
        if value and value  float:
        return sum(item.total_price for item in self.items)

@app.post("/orders")
async def create_order(order: OrderRequest):
    # order is fully parsed and validated
    # All business rules are enforced
    # Type safety is guaranteed
    
    order_id = create_order_in_db(order)
    return {
        "order_id": order_id,
        "total_amount": order.total_amount,
        "customer_email": order.customer_email,
        "items_count": len(order.items)
    }
```

### Custom Field Types for Domain Logic

```python
class ISBN(str):
    """International Standard Book Number with validation."""
    
    @classmethod
    def validate(cls, value: str) -> 'ISBN':
        # Remove hyphens and spaces
        cleaned = re.sub(r'[-\s]', '', value)
        
        if len(cleaned) not in [10, 13]:
            raise ValueError("ISBN must be 10 or 13 digits")
            
        if not cleaned.isdigit():
            raise ValueError("ISBN must contain only digits")
            
        # Add checksum validation logic here
        return cls(value)

class Money(BaseModel):
    """Money type with currency validation."""
    amount: Annotated[float, Field(ge=0)]
    currency: str = Field(pattern=r'^[A-Z]{3}$', description="3-letter currency code")
    
    def __add__(self, other: 'Money') -> 'Money':
        if self.currency != other.currency:
            raise ValueError("Cannot add different currencies")
        return Money(amount=self.amount + other.amount, currency=self.currency)

class Book(BaseModel):
    isbn: ISBN
    title: str = Field(min_length=1, max_length=200)
    price: Money
    publication_date: date
    
    @field_validator('publication_date')
    @classmethod
    def validate_publication_date(cls, value: date) -> date:
        if value > date.today():
            raise ValueError("Publication date cannot be in the future")
        return value

@app.post("/books")
async def add_book(book: Book):
    # book.isbn is guaranteed to be valid ISBN
    # book.price is validated Money object
    # All validation rules are enforced
    return {"message": f"Book {book.title} added successfully"}
```

## Advanced Patterns

### Discriminated Unions for Parsing Different Input Types

```python
from typing import Union, Literal
from pydantic import BaseModel, Field, Discriminator

class EmailContact(BaseModel):
    type: Literal["email"] = "email"
    email: EmailAddress

class PhoneContact(BaseModel):
    type: Literal["phone"] = "phone"
    phone: str = Field(pattern=r'^\+?1?\d{9,15}$')

class AddressContact(BaseModel):
    type: Literal["address"] = "address" 
    address: DeliveryAddress

Contact = Union[EmailContact, PhoneContact, AddressContact]

class CustomerProfile(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    preferred_contact: Contact = Field(discriminator='type')
    backup_contacts: List[Contact] = Field(default_factory=list)

@app.post("/customers")
async def create_customer(profile: CustomerProfile):
    # FastAPI automatically parses the correct contact type
    # based on the discriminator field
    if profile.preferred_contact.type == "email":
        send_welcome_email(profile.preferred_contact.email)
    
    return {"customer_id": generate_id(), "profile": profile}
```

### Context-Dependent Validation

```python
from contextvars import ContextVar
from pydantic import BaseModel, field_validator, ValidationInfo

user_context: ContextVar[dict] = ContextVar('user_context')

class RestrictedContent(BaseModel):
    title: str
    content: str
    min_age_required: int = Field(ge=0, le=21)
    
    @field_validator('content')
    @classmethod
    def validate_content_access(cls, value: str, info: ValidationInfo) -> str:
        if info.context and 'user_age' in info.context:
            user_age = info.context['user_age']
            min_age = info.context.get('min_age_required', 0)
            
            if user_age < min_age:
                raise ValueError("User not old enough to access this content")
                
        return value

@app.post("/content")
async def create_content(
    content: RestrictedContent,
    user_age: int = Query(ge=0, le=150)
):
    # Validate with context
    validated_content = RestrictedContent.model_validate(
        content.model_dump(),
        context={'user_age': user_age, 'min_age_required': content.min_age_required}
    )
    
    return {"message": "Content created", "content": validated_content}
```

## Benefits and Best Practices

### Key Advantages

1. **Early Error Detection**: Invalid data is caught at the system boundary before any processing occurs
2. **Type Safety**: Once parsed, data carries proof of validity in its type
3. **Reduced Redundant Checks**: No need to re-validate already parsed data
4. **Clear API Contracts**: Pydantic models serve as documentation
5. **Automatic OpenAPI Generation**: FastAPI generates accurate API documentation

### Best Practices

1. **Design Rich Domain Types**:
   ```python
   # Instead of primitive obsession
   def process_user(user_id: int, email: str, age: int): ...
   
   # Use rich domain types
   def process_user(user: ValidatedUser): ...
   ```

2. **Parse at Boundaries**:
   ```python
   @app.post("/api/endpoint")
   async def endpoint(data: WellDefinedModel):
       # All validation happens here automatically
       # Business logic can trust the data structure
       return process_business_logic(data)
   ```

3. **Use Composition for Complex Validation**:
   ```python
   class Address(BaseModel): ...
   class PaymentMethod(BaseModel): ...
   
   class Order(BaseModel):
       shipping_address: Address  # Composed validation
       billing_address: Address
       payment: PaymentMethod
       
       @model_validator(mode='after')
       def validate_business_rules(self):
           # Cross-field business logic validation
           return self
   ```

4. **Leverage Annotated Types**:
   ```python
   PositiveFloat = Annotated[float, Field(gt=0)]
   NonEmptyString = Annotated[str, Field(min_length=1)]
   
   # Reusable across multiple models
   class Product(BaseModel):
       name: NonEmptyString
       price: PositiveFloat
   ```

The "Parse, Don't Validate" principle combined with Pydantic and FastAPI creates a robust foundation for building type-safe, well-validated APIs. By transforming raw input into rich, validated domain objects early in the request lifecycle, you eliminate entire classes of bugs and create more maintainable, reliable applications.

[1] https://www.sussex.ac.uk/informatics/punctuation/hyphenanddash/hyphen
[2] https://en.wikipedia.org/wiki/P
[3] https://www.merriam-webster.com/dictionary/a
[4] https://en.wikipedia.org/wiki/R_(programming_language)
[5] https://en.wikipedia.org/wiki/S
[6] https://en.wikipedia.org/wiki/E_(mathematical_constant)
[7] https://en.wikipedia.org/wiki/Vitamin_D
[8] https://wmich.edu/writing/punctuation/hyphen
[9] https://www.youtube.com/watch?v=yTCDVfMz15M
[10] https://en.wiktionary.org/wiki/a
[11] https://www.w3schools.com/r/r_intro.asp
[12] https://www.youtube.com/watch?v=yYchF3OLkm4
[13] https://en.wikipedia.org/wiki/E
[14] https://kidshealth.org/en/parents/vitamin-d.html
[15] https://developers.google.com/style/hyphens
[16] https://www.youtube.com/watch?v=5DuZkK_trYY
[17] https://en.wikipedia.org/wiki/A_(disambiguation)
[18] https://www.codecademy.com/learn/learn-r
[19] https://www.youtube.com/watch?v=7s5FUVc4mkc
[20] https://www.eonline.com/ca
[21] https://www.linkedin.com/pulse/parse-dont-validate-yevhen-tytov-vzebf
[22] https://github.com/tiangolo/fastapi/discussions/9853
[23] https://fastapi.tiangolo.com/tutorial/body-fields/
[24] https://dev.to/zoedsoupe/parse-dont-validate-embracing-data-integrity-in-elixir-5c94
[25] https://fastapi.tiangolo.com/tutorial/query-params-str-validations/
[26] https://fastapi.tiangolo.com/tutorial/extra-models/
[27] https://deviq.com/practices/parse-dont-validate/
[28] https://stackoverflow.com/questions/78767465/why-cant-my-fastapi-router-parse-pydantics-enum-type-when-i-use-union-params
[29] https://www.linkedin.com/pulse/best-way-use-pydantic-fastapi-detailed-guide-manikandan-parasuraman-du7cc
[30] https://www.reddit.com/r/programming/comments/1m808e1/what_parse_dont_validate_means_in_python/
[31] https://news.ycombinator.com/item?id=27639890
[32] https://www.getorchestra.io/guides/pydantic-custom-types-in-fastapi-a-comprehensive-guide
[33] https://lexi-lambda.github.io/blog/2019/11/05/parse-don-t-validate/
[34] https://www.reddit.com/r/Python/comments/16xnhim/what_problems_does_pydantic_solves_and_how_should/
[35] https://docs.pydantic.dev/latest/concepts/types/
[36] https://www.youtube.com/watch?v=KQVy0CaB7ds
[37] https://docs.pydantic.dev/latest/concepts/validators/
[38] https://fastapi.tiangolo.com/python-types/
[39] https://news.ycombinator.com/item?id=39322551
[40] https://docs.pydantic.dev/latest/concepts/models/
[41] https://docs.pydantic.dev/1.10/usage/types/
[42] https://py-nt.asyncmove.com/examples/using_with_pydantic/
[43] https://dev.to/saleor/branded-types-in-typescript-techniques-340f
[44] https://docs.pydantic.dev/2.0/usage/types/types/
[45] https://stackoverflow.com/questions/72268685/pydantic-checks-on-newtype
[46] https://www.youtube.com/watch?v=VhmbMAXnlBc
[47] https://docs.pydantic.dev/latest/api/types/
[48] https://stackoverflow.com/questions/50563546/validating-detailed-types-in-python-dataclasses
[49] https://github.com/pydantic/pydantic/pull/115
[50] https://news.ycombinator.com/item?id=40146751
[51] https://docs.pydantic.dev/latest/api/standard_library_types/
[52] https://discuss.python.org/t/generic-newtype/61234
[53] https://stackoverflow.com/questions/43633891/validating-a-data-type-in-python
[54] https://dev.to/mechcloud_academy/advanced-pydantic-generic-models-custom-types-and-performance-tricks-4opf
[55] https://github.com/pydantic/pydantic/issues/5907
[56] https://www.reddit.com/r/typescript/comments/1ff1fta/discussion_can_you_overuse_branded_types/
[57] https://docs.pydantic.dev/2.0/api/types/
[58] https://docs.pydantic.dev/1.10/usage/validators/
[59] https://www.geeksforgeeks.org/python/fastapi-pydantic/
[60] http://stephantul.github.io/python/typing/2024/04/08/newtype/
[61] https://docs.pydantic.dev/latest/examples/custom_validators/
[62] https://codesignal.com/learn/courses/working-with-data-models-in-fastapi/lessons/handling-post-requests-with-pydantic-models
[63] https://docs.python.org/3/library/typing.html
[64] https://docs.pydantic.dev/2.9/concepts/validators/
[65] https://www.reddit.com/r/golang/comments/kmj640/newtypes_constructing_and_validation/
[66] https://data-ai.theodo.com/en/technical-blog/fastapi-pydantic-powerful-duo
[67] https://stackoverflow.com/questions/65964860/why-does-the-newtype-function-not-check-for-the-correct-variable-type
[68] https://stackoverflow.com/questions/77100890/pydantic-v2-custom-type-validators-with-info
[69] https://fastapi.tiangolo.com/tutorial/schema-extra-example/
[70] https://realpython.com/python-pydantic/
[71] https://www.youtube.com/watch?v=ba_9c6D0ruc
[72] https://github.com/python/typing/issues/415
[73] https://docs.pydantic.dev/2.0/usage/validators/
[74] https://www.mindbowser.com/fastapi-data-validation-pydantic/
[75] https://docs.pydantic.dev/2.8/concepts/validators/
[76] https://fastapi.tiangolo.com/tutorial/path-params/
[77] https://www.linkedin.com/pulse/best-practices-using-pydantic-python-nuno-bispo-hooke
[78] https://fastapi.tiangolo.com/tutorial/body/
[79] https://fastapi.tiangolo.com/tutorial/query-params/
[80] https://www.prefect.io/blog/what-is-pydantic-validating-data-in-python
[81] https://iamabbey.hashnode.dev/custom-types-in-pydantic
[82] https://stackoverflow.com/questions/64932222/when-where-to-use-body-path-query-field-in-fastapi
[83] https://stackoverflow.com/questions/76910486/how-to-enforce-fast-api-to-use-path-body-and-query-parameters
[84] https://www.speakeasy.com/blog/pydantic-vs-dataclasses
[85] https://github.com/pydantic/pydantic/discussions/9859
[86] https://www.prefect.io/blog/pydantic-enums-introduction
[87] https://gpttutorpro.com/fastapi-basics-path-parameters-query-parameters-and-request-body/