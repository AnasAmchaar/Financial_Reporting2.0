```python
# config.py
class Config:
    """
    Configuration class for the application.
    """

    def __init__(self, api_key, api_secret, base_url):
        """
        Initializes the Config instance.

        Args:
            api_key (str): The API key for authentication.
            api_secret (str): The API secret for authentication.
            base_url (str): The base URL for API requests.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url

    def get_api_headers(self):
        """
        Returns the API headers for authentication.

        Returns:
            dict: A dictionary containing the API key and secret.
        """
        return {
            'Authorization': f'Bearer {self.api_key}',
            'X-API-SECRET': self.api_secret
        }
```

```python
# api_client.py
import requests
from config import Config

class APIClient:
    """
    API client class for making requests to the API.
    """

    def __init__(self, config: Config):
        """
        Initializes the APIClient instance.

        Args:
            config (Config): The configuration instance.
        """
        self.config = config
        self.base_url = config.base_url

    def get(self, endpoint: str, params: dict = None):
        """
        Makes a GET request to the API.

        Args:
            endpoint (str): The API endpoint.
            params (dict, optional): The query parameters. Defaults to None.

        Returns:
            requests.Response: The response from the API.
        """
        headers = self.config.get_api_headers()
        if params:
            return requests.get(f'{self.base_url}{endpoint}', params=params, headers=headers)
        return requests.get(f'{self.base_url}{endpoint}', headers=headers)

    def post(self, endpoint: str, data: dict):
        """
        Makes a POST request to the API.

        Args:
            endpoint (str): The API endpoint.
            data (dict): The request body.

        Returns:
            requests.Response: The response from the API.
        """
        headers = self.config.get_api_headers()
        return requests.post(f'{self.base_url}{endpoint}', json=data, headers=headers)
```

```python
# main.py
from config import Config
from api_client import APIClient

def main():
    config = Config('api_key', 'api_secret', 'https://api.example.com')
    api_client = APIClient(config)

    response = api_client.get('/users')
    print(response.json())

    data = {'name': 'John Doe', 'email': 'john@example.com'}
    response = api_client.post('/users', data)
    print(response.json())

if __name__ == '__main__':
    main()
```