docker-compose up --build
docker exec -it mongo1 mongosh < ./mongo-init/rs-init.js

docker stop mongo1
docker start mongo1

curl http://localhost:6000
curl http://localhost:5001/health

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://www.cse.wustl.edu/~jain/ehms/ftp/wustl-ehms-2020_with_attacks_categories.csv",
        "tenantId": "WUSTL"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/alibaba/clusterdata/refs/heads/master/cluster-trace-gpu-v2023/csv/openb_node_list_gpu_node.csv",
        "tenantId": "Alibaba"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/alibaba/clusterdata/refs/heads/master/cluster-trace-gpu-v2023/csv/openb_pod_list_multigpu50.csv",
        "tenantId": "Alibaba"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/alibaba/clusterdata/refs/heads/master/cluster-trace-gpu-v2023/csv/openb_pod_list_multigpu40.csv",
        "tenantId": "Alibaba"
        }'

curl "http://localhost:5001/data?tenantId=NIH&limit=5"

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/Azure/AzurePublicDataset/refs/heads/master/data/AzureLLMInferenceTrace_code.csv",
        "tenantId": "Azure"
        }'

curl "http://localhost:5001/data?tenantId=Azure&limit=5"

docker logs mysimbdp-coredms

docker compose down -v