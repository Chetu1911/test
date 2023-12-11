"""Weaviate reader."""

from typing import Any, List, Optional

from nextpy.ai.rag.document_loaders.basereader import BaseReader
from nextpy.ai.schema import DocumentNode


class WeaviateReader(BaseReader):
    """Weaviate reader.

    Retrieves documents from Weaviate through vector lookup. Allows option
    to concatenate retrieved documents into one DocumentNode, or to return
    separate DocumentNode objects per DocumentNode.

    Args:
        host (str): host.
        auth_client_secret (Optional[weaviate.auth.AuthCredentials]):
            auth_client_secret.
    """

    def __init__(
        self,
        host: str,
        auth_client_secret: Optional[Any] = None,
    ) -> None:
        """Initialize with parameters."""
        from weaviate import Client  # noqa: F401

        self.host = host
        self.client: Client = Client(host, auth_client_secret=auth_client_secret)

    def load_data(
        self,
        class_name: Optional[str] = None,
        properties: Optional[List[str]] = None,
        graphql_query: Optional[str] = None,
        separate_documents: Optional[bool] = True,
    ) -> List[DocumentNode]:
        """Load data from Weaviate.

        If `graphql_query` is not found in load_kwargs, we assume that
        `class_name` and `properties` are provided.

        Args:
            class_name (Optional[str]): class_name to retrieve documents from.
            properties (Optional[List[str]]): properties to retrieve from documents.
            graphql_query (Optional[str]): Raw GraphQL Query.
                We assume that the query is a Get query.
            separate_documents (Optional[bool]): Whether to return separate
                documents. Defaults to True.

        Returns:
            List[DocumentNode]: A list of documents.

        """
        metadata = {
            "host": self.host,
            "class_name": class_name,
            "properties": properties,
            "graphql_query": graphql_query,
        }

        if class_name is not None and properties is not None:
            props_txt = "\n".join(properties)
            graphql_query = f"""
            {{
                Get {{
                    {class_name} {{
                        {props_txt}
                    }}
                }}
            }}
            """
        elif graphql_query is not None:
            pass
        else:
            raise ValueError(
                "Either `class_name` and `properties` must be specified, "
                "or `graphql_query` must be specified."
            )

        response = self.client.query.raw(graphql_query)
        if "errors" in response:
            raise ValueError("Invalid query, got errors: {}".format(response["errors"]))

        data_response = response["data"]
        if "Get" not in data_response:
            raise ValueError("Invalid query response, must be a Get query.")

        if class_name is None:
            # infer class_name if only graphql_query was provided
            class_name = list(data_response["Get"].keys())[0]
        entries = data_response["Get"][class_name]
        documents = []
        for entry in entries:
            embedding = None
            # for each entry, join properties into <property>:<value>
            # separated by newlines
            text_list = []
            for k, v in entry.items():
                if k == "_additional":
                    if "vector" in v:
                        embedding = v["vector"]
                    continue
                text_list.append(f"{k}: {v}")

            text = "\n".join(text_list)
            documents.append(
                DocumentNode(text=text, embedding=embedding, extra_info=metadata)
            )

        if not separate_documents:
            # join all documents into one
            text_list = [doc.get_text() for doc in documents]
            text = "\n\n".join(text_list)
            documents = [DocumentNode(text=text, extra_info=metadata)]

        return documents
