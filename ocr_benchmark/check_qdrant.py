import qdrant_client
client = qdrant_client.QdrantClient(':memory:')
print("search:", hasattr(client, 'search'))
print("methods:", [x for x in dir(client) if 'search' in x or 'query' in x])
