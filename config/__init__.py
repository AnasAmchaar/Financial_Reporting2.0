```python
# Import required libraries
import os
import logging
from typing import Dict, List

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class User:
    """
    Represents a user with a unique ID and name.

    Attributes:
        id (int): Unique identifier for the user.
        name (str): Name of the user.
    """

    def __init__(self, id: int, name: str):
        """
        Initializes a User object.

        Args:
            id (int): Unique identifier for the user.
            name (str): Name of the user.
        """
        self.id = id
        self.name = name

class UserRepository:
    """
    Manages a collection of User objects.

    Attributes:
        users (Dict[int, User]): Mapping of user IDs to User objects.
    """

    def __init__(self):
        """
        Initializes an empty UserRepository.
        """
        self.users = {}

    def add_user(self, user: User) -> None:
        """
        Adds a User object to the repository.

        Args:
            user (User): User object to add.
        """
        self.users[user.id] = user

    def get_user(self, user_id: int) -> User:
        """
        Retrieves a User object by ID.

        Args:
            user_id (int): ID of the user to retrieve.

        Returns:
            User: User object with the specified ID, or None if not found.
        """
        return self.users.get(user_id)

class UserService:
    """
    Provides business logic for user management.

    Attributes:
        repository (UserRepository): Repository for user data.
    """

    def __init__(self, repository: UserRepository):
        """
        Initializes a UserService object.

        Args:
            repository (UserRepository): Repository for user data.
        """
        self.repository = repository

    def create_user(self, id: int, name: str) -> User:
        """
        Creates a new User object and adds it to the repository.

        Args:
            id (int): Unique identifier for the user.
            name (str): Name of the user.

        Returns:
            User: Newly created User object.
        """
        user = User(id, name)
        self.repository.add_user(user)
        return user

    def get_user(self, user_id: int) -> User:
        """
        Retrieves a User object by ID.

        Args:
            user_id (int): ID of the user to retrieve.

        Returns:
            User: User object with the specified ID, or None if not found.
        """
        return self.repository.get_user(user_id)

# Example usage
if __name__ == '__main__':
    # Create a new UserRepository
    repository = UserRepository()

    # Create a new UserService with the repository
    service = UserService(repository)

    # Create a new user
    user = service.create_user(1, 'John Doe')

    # Retrieve the user by ID
    retrieved_user = service.get_user(1)

    # Print the user's name
    if retrieved_user:
        logging.info(f'User name: {retrieved_user.name}')
    else:
        logging.info('User not found')
```

```python
# Import required libraries
import os
import logging
from typing import Dict, List

# Set up logging configuration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class User:
    """
    Represents a user with a unique ID and name.

    Attributes:
        id (int): Unique identifier for the user.
        name (str): Name of the user.
    """

    def __init__(self, id: int, name: str):
        """
        Initializes a User object.

        Args:
            id (int): Unique identifier for the user.
            name (str): Name of the user.
        """
        self.id = id
        self.name = name

class UserRepository:
    """
    Manages a collection of User objects.

    Attributes:
        users (Dict[int, User]): Mapping of user IDs to User objects.
    """

    def __init__(self):
        """
        Initializes an empty UserRepository.
        """
        self.users: Dict[int, User] = {}

    def add_user(self, user: User) -> None:
        """
        Adds a User object to the repository.

        Args:
            user (User): User object to add.
        """
        self.users[user.id] = user

    def get_user(self, user_id: int) -> User:
        """
        Retrieves a User object by ID.

        Args:
            user_id (int): ID of the user to retrieve.

        Returns:
            User: User object with the specified ID, or None if not found.
        """
        return self.users.get(user_id)

class UserService:
    """
    Provides business logic for user management.

    Attributes:
        repository (UserRepository): Repository for user data.
    """

    def __init__(self, repository: UserRepository):
        """
        Initializes a UserService object.

        Args:
            repository (UserRepository): Repository for user data.
        """
        self.repository: UserRepository = repository

    def create_user(self, id: int, name: str) -> User:
        """
        Creates a new User object and adds it to the repository.

        Args:
            id (int): Unique identifier for the user.
            name (str): Name of the user.

        Returns:
            User: Newly created User object.
        """
        user = User(id, name)
        self.repository.add_user(user)
        return user

    def get_user(self, user_id: int) -> User:
        """
        Retrieves a User object by ID.

        Args:
            user_id (int): ID of the user to retrieve.

        Returns:
            User: User object with the specified ID, or None if not found.
        """
        return self.repository.get_user(user_id)

# Example usage
if __name__ == '__main__':
    # Create a new UserRepository
    repository = UserRepository()

    # Create a new UserService with the repository
    service = UserService(repository)

    # Create a new user
    user = service.create_user(1, 'John Doe')

    # Retrieve the user by ID
    retrieved_user = service.get_user(1)

    # Print the user's name
    if retrieved_user:
        logging.info(f'User name: {retrieved_user.name}')
    else:
        logging.info('User not found')
```