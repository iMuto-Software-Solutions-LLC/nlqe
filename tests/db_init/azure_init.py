import time
from azure.storage.blob import BlobServiceClient

conn_str = 'DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;'

for i in range(20):
    try:
        service = BlobServiceClient.from_connection_string(conn_str)
        service.create_container('test-container')
        print('Container test-container created')
        break
    except Exception as e:
        if 'ContainerAlreadyExists' in str(e):
            print('Container already exists')
            break
        print(f'Retry {i}: {e}')
        time.sleep(2)
