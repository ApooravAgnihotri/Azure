from dotenv import dotenv_values 
# specify the name of the .env file name 
env_name = "config.env"
config = dotenv_values(env_name)

print("---- configuration loaded ----")

# Load Azure SQL database connection details
server = config["server"] 
database = config["database"] 
username = config["username"] 
password = config["password"] 
driver = '{ODBC Driver 18 for SQL Server}'


# Load Open AI deployment details
import openai
openai.api_type = config["openai_api_type"]
openai.api_key = config['openai_api_key']
openai.api_base = config['openai_api_base']
openai.api_version = config['openai_api_version'] 
openai_deployment = config["openai_deployment_embedding"]
EMBEDDING_LENGTH = 1536


# Load Cognitive Search service details
cogsearch_key = config["cogsearch_api_key"]
service_endpoint = config["cogsearch_endpoint"]
index_name = config["cogsearch_index_name"] # Desired name of index -- does not need to exist already

print("--- Load Cognitive Search service details setup ---")


import pyodbc

# Create a connection string
conn_str = f"DRIVER={driver};SERVER={server};DATABASE={database};UID={username};PWD={password}"

# Establish a connection to the Azure SQL database
conn = pyodbc.connect(conn_str, autocommit=True)
cursor = conn.cursor()

print("--- Cnnection Established---")


table_name = "vwEdrLogsDetailByShivi" 

# Execute the SELECT statement
try:
    cursor.execute(f"SELECT count(Id) FROM {table_name};")
    rows = cursor.fetchall()
    for row in rows:
        print(row)
except Exception as e:
    print(f"Error executing SELECT statement: {e}")


# Set up data source connection in Cog Search
# Import needed CogSearch functions

from azure.core.credentials import AzureKeyCredential  
from azure.search.documents import SearchClient  
from azure.search.documents.indexes import SearchIndexClient, SearchIndexerClient  
from azure.search.documents.models import (
    QueryAnswerType,
    QueryCaptionType,
    QueryLanguage,
    QueryType,
    RawVectorQuery,
    VectorizableTextQuery,
    VectorFilterMode,    
)
from azure.search.documents.indexes.models import (  
    AzureOpenAIEmbeddingSkill,  
    AzureOpenAIParameters,  
    AzureOpenAIVectorizer,  
    ExhaustiveKnnParameters,  
    ExhaustiveKnnVectorSearchAlgorithmConfiguration,
    FieldMapping,  
    HnswParameters,  
    HnswVectorSearchAlgorithmConfiguration,  
    IndexProjectionMode,  
    InputFieldMappingEntry,
    MergeSkill,
    OutputFieldMappingEntry,  
    PrioritizedFields,    
    SearchField,  
    SearchFieldDataType,  
    SearchIndex,  
    SearchIndexer,  
    SearchIndexerDataContainer,  
    SearchIndexerDataSourceConnection,  
    SearchIndexerIndexProjectionSelector,  
    SearchIndexerIndexProjections,  
    SearchIndexerIndexProjectionsParameters,  
    SearchIndexerSkillset,  
    SemanticConfiguration,  
    SemanticField,  
    SemanticSettings,  
    SplitSkill,  
    SqlIntegratedChangeTrackingPolicy,
    VectorSearch,  
    VectorSearchAlgorithmKind,  
    VectorSearchAlgorithmMetric,  
    VectorSearchProfile,  
)  

print("--- Imported needed CogSearch functions ---")

# Create data source connection
# This step creates a connection that will be used to pull data from our SQL table.
ds_conn_str = f'Encrypt=True;TrustServerCertificate=False;Connection Timeout=30;Server=tcp:{server};Database={database};User ID={username};Password={password};'

cogsearch_credential = AzureKeyCredential(cogsearch_key)
ds_client = SearchIndexerClient(service_endpoint, cogsearch_credential)
container = SearchIndexerDataContainer(name=table_name)

change_detection_policy = SqlIntegratedChangeTrackingPolicy()

data_source_connection = SearchIndexerDataSourceConnection(
    name=f"{index_name}-azuresql-connection",
    type="azuresql",
    connection_string=ds_conn_str,
    container=container,
    data_change_detection_policy=change_detection_policy
)
data_source = ds_client.create_or_update_data_source_connection(data_source_connection)

print(f"Data source '{data_source.name}' created or updated")


# # Create a search index
# index_client = SearchIndexClient(
#     endpoint=service_endpoint, credential=cogsearch_credential)

# fields = [
#     # Properties of individual chunk
#     SearchField(name="Id", type=SearchFieldDataType.String, key=True,
#                 sortable=True, filterable=True, facetable=True, analyzer_name="keyword"),
#     SearchField(name="chunk", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
#     SearchField(name="vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
#                 vector_search_dimensions=EMBEDDING_LENGTH, vector_search_profile="my-vector-search-profile"),
#     # Properties of original row in DB that the chunk belonged to
#     SearchField(name="parent_id", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
#     SearchField(name="parent_product_id", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
#     SearchField(name="parent_text", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
#     SearchField(name="parent_summary", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
#     SearchField(name="parent_score", type=SearchFieldDataType.Int64, sortable=True, filterable=True, facetable=True)
# ]

# # Configure the vector search configuration  
# vector_search = VectorSearch(
#     algorithms=[
#         HnswVectorSearchAlgorithmConfiguration(
#             name="my-hnsw-config",
#             kind=VectorSearchAlgorithmKind.HNSW
#         )
#     ],
#     profiles=[
#         VectorSearchProfile(
#             name="my-vector-search-profile",
#             algorithm="my-hnsw-config",
#             vectorizer="my-openai"
#         )
#     ],
#     vectorizers=[
#         AzureOpenAIVectorizer(
#             name="my-openai",
#             kind="azureOpenAI",
#             azure_open_ai_parameters=AzureOpenAIParameters(
#                 resource_uri=openai.api_base,
#                 deployment_id=openai_deployment,
#                 api_key=openai.api_key
#             )
#         )  
#     ]  
# )

# semantic_config = SemanticConfiguration(
#     name="my-semantic-config",
#     prioritized_fields=PrioritizedFields(
#         prioritized_content_fields=[SemanticField(field_name="Id")]
#     )
# )

# # Create the semantic settings with the configuration
# semantic_settings = SemanticSettings(configurations=[semantic_config])

# # Create the search index with the semantic settings
# index = SearchIndex(name=index_name, fields=fields,
#                     vector_search=vector_search, semantic_settings=semantic_settings)
# result = index_client.create_or_update_index(index)
# print(f'{result.name} created')