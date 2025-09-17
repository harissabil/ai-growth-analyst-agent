import os
from typing import Optional

from azure.cosmos import ContainerProxy, CosmosClient, DatabaseProxy, PartitionKey
from dotenv import find_dotenv, load_dotenv


class CosmosDBClient:
    """Singleton client for Azure Cosmos DB operations."""

    _instance: Optional["CosmosDBClient"] = None

    def __new__(cls) -> "CosmosDBClient":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, "initialized"):
            load_dotenv(find_dotenv(), override=False)

            # Load configuration from environment
            self.endpoint = os.getenv("COSMOS_DB_ENDPOINT")
            self.key = os.getenv("COSMOS_DB_KEY")
            self.database_name = os.getenv("COSMOS_DB_DATABASE", "ai_growth_analyst_db")
            self.chat_history_container = os.getenv("COSMOS_DB_HISTORY_CONTAINER", "chat_history")
            self.chat_messages_container = os.getenv("COSMOS_DB_MESSAGES_CONTAINER", "chat_messages")

            if not self.endpoint or not self.key:
                raise RuntimeError("COSMOS_DB_ENDPOINT and COSMOS_DB_KEY must be set")

            # Initialize client
            self.client = CosmosClient(self.endpoint, self.key)
            self.database: Optional[DatabaseProxy] = None
            self.history_container: Optional[ContainerProxy] = None
            self.messages_container: Optional[ContainerProxy] = None

            self.initialized = True

    def initialize_containers(self) -> None:
        """Initialize database and containers with proper partition keys."""
        try:
            # Create or get database
            self.database = self.client.create_database_if_not_exists(id=self.database_name)

            # Create chat_history container with user_id as partition key
            self.history_container = self.database.create_container_if_not_exists(
                id=self.chat_history_container,
                partition_key=PartitionKey(path="/user_id", kind="Hash"),
            )

            # Create chat_messages container with chat_history_id as partition key
            self.messages_container = self.database.create_container_if_not_exists(
                id=self.chat_messages_container,
                partition_key=PartitionKey(path="/chat_history_id", kind="Hash"),
            )

        except Exception as e:
            raise RuntimeError(f"Failed to initialize Cosmos DB containers: {e}")

    def get_history_container(self) -> ContainerProxy:
        """Get the chat history container."""
        if not self.history_container:
            self.initialize_containers()
        return self.history_container

    def get_messages_container(self) -> ContainerProxy:
        """Get the chat messages container."""
        if not self.messages_container:
            self.initialize_containers()
        return self.messages_container


# Global client instance
cosmos_client = CosmosDBClient()
