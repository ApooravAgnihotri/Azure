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

# cursor.close()

# print(" --- closing the database ---")


table_name = "pk_QA_test" 

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
    #IndexProjectionMode,  
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
    #VectorSearchAlgorithmMetric,  
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


# Create a search index
index_client = SearchIndexClient(
    endpoint=service_endpoint, credential=cogsearch_credential)

fields = [
    # Properties of individual chunk
    SearchField(name="Id", type=SearchFieldDataType.String, key=True,
                sortable=True, filterable=True, facetable=True, analyzer_name="keyword"),
    SearchField(name="chunk", type=SearchFieldDataType.String, sortable=False, filterable=False, facetable=False),
    SearchField(name="vector", type=SearchFieldDataType.Collection(SearchFieldDataType.Single), 
                vector_search_dimensions=EMBEDDING_LENGTH, vector_search_profile="my-vector-search-profile"),
    # Properties of original row in DB that the chunk belonged to
    SearchField(name="id", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
    SearchField(name="question", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
    SearchField(name="answer", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True)

    # SearchField(name="parent_summary", type=SearchFieldDataType.String, sortable=True, filterable=True, facetable=True),
    # SearchField(name="parent_score", type=SearchFieldDataType.Int64, sortable=True, filterable=True, facetable=True)
]

# Configure the vector search configuration  
vector_search = VectorSearch(
    algorithms=[
        HnswVectorSearchAlgorithmConfiguration(
            name="my-hnsw-config",
            kind=VectorSearchAlgorithmKind.HNSW
        )
    ],
    profiles=[
        VectorSearchProfile(
            name="my-vector-search-profile",
            algorithm="my-hnsw-config",
            vectorizer="my-openai"
        )
    ],
    vectorizers=[
        AzureOpenAIVectorizer(
            name="my-openai",
            kind="azureOpenAI",
            azure_open_ai_parameters=AzureOpenAIParameters(
                resource_uri=openai.api_base,
                deployment_id=openai_deployment,
                api_key=openai.api_key
            )
        )  
    ]  
)

semantic_config = SemanticConfiguration(
    name="my-semantic-config",
    prioritized_fields=PrioritizedFields(
        prioritized_content_fields=[SemanticField(field_name="Id")]
    )
)

# Create the semantic settings with the configuration
semantic_settings = SemanticSettings(configurations=[semantic_config])

# Create the search index with the semantic settings
index = SearchIndex(name=index_name, fields=fields,
                    vector_search=vector_search, semantic_settings=semantic_settings)
result = index_client.create_or_update_index(index)
print(f'{result.name} created')


# # Create a skillset  
# skillset_name = f"{index_name}-skillset"

# split_skill = SplitSkill(  
#     description="Split skill to chunk documents",  
#     text_split_mode="pages",  
#     context="/document",  
#     maximum_page_length=300,  
#     page_overlap_length=20,  
#     inputs=[  
#         InputFieldMappingEntry(name="text", source="/document/TextConcat"),  
#     ],  
#     outputs=[  
#         OutputFieldMappingEntry(name="textItems", target_name="pages")  
#     ]  
# )

# embedding_skill = AzureOpenAIEmbeddingSkill(  
#     description="Skill to generate embeddings via Azure OpenAI",  
#     context="/document/pages/*",  
#     resource_uri=openai.api_base,  
#     deployment_id=openai_deployment,  
#     api_key=openai.api_key,  
#     inputs=[  
#         InputFieldMappingEntry(name="text", source="/document/pages/*"),  
#     ],  
#     outputs=[  
#         OutputFieldMappingEntry(name="embedding", target_name="vector")  
#     ]  
# )  

# index_projections = SearchIndexerIndexProjections(  
#     selectors=[  
#         SearchIndexerIndexProjectionSelector(  
#             target_index_name=index_name,  
#             parent_key_field_name="parent_id", # Note: this populates the "parent_id" search field
#             source_context="/document/pages/*",  
#             mappings=[  
#                 InputFieldMappingEntry(name="chunk", source="/document/pages/*"),
#                 InputFieldMappingEntry(name="vector", source="/document/pages/*/vector"),
#                 InputFieldMappingEntry(name="parent_product_id", source="/document/ProductId"),
#                 InputFieldMappingEntry(name="parent_text", source="/document/Text"),
#                 InputFieldMappingEntry(name="parent_summary", source="/document/Summary"),
#                 InputFieldMappingEntry(name="parent_score", source="/document/Score")
#             ],  
#         ),  
#     ],
# )  

# skillset = SearchIndexerSkillset(  
#     name=skillset_name,  
#     description="Skillset to chunk documents and generating embeddings",  
#     skills=[split_skill, embedding_skill],
#     index_projections=index_projections  
# )
  
# client = SearchIndexerClient(service_endpoint, cogsearch_credential)  
# client.create_or_update_skillset(skillset)  
# print(f' {skillset.name} created')


# # Create an indexer  
# indexer_name = f"{index_name}-indexer"  

# indexer = SearchIndexer(  
#     name=indexer_name,  
#     description="Indexer to chunk documents and generate embeddings",  
#     skillset_name=skillset_name,  
#     target_index_name=index_name,  
#     data_source_name=data_source.name
# )  
  
# indexer_client = SearchIndexerClient(service_endpoint, cogsearch_credential)
# indexer_result = indexer_client.create_or_update_indexer(indexer)  

# # Run the indexer  
# indexer_client.run_indexer(indexer_name)
# print(f' {indexer_name} created')

# # Get the status of the indexer  
# indexer_status = indexer_client.get_indexer_status(indexer_name)
# print(f"Indexer status: {indexer_status.status}")

# # Allow some time for the indexer to process the data
# import time
# time.sleep(30)

user_query = "What is a DDoS attack?"

search_client = SearchClient(service_endpoint, index_name, credential=cogsearch_credential)
vector_query = VectorizableTextQuery(text=user_query, k=3, fields="vector", exhaustive=True)
# Use the query below to pass in the raw vector query instead of the query vectorization
#vector_query = RawVectorQuery(vector=generate_embeddings(user_query), k=3, fields="vector")
  
results = search_client.search(
    search_text=None,  
    vector_queries= [vector_query],
    select=["Id","chunk", "id", "question", "answer"],
    top=3
)


for result in results:
    print(f"Search score: {result['@search.score']}")
    print(f"Chunk id: {result['Id']}")
    print(f"question : {result['queston']}")
    print(f"answer: {result['answer']}")
    # print(f"Product Id: {result['parent_product_id']}")
    # print(f"Text chunk: {result['chunk']}") 
    # print(f"Review summary: {result['parent_summary']}")
    # print(f"Review text: {result['parent_text']}")
    # print(f"Review score: {result['parent_score']}")
    print("-----")