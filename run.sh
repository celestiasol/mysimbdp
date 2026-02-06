docker-compose up --build

docker exec -i mongo-configsvr1 mongosh --port 27019 --file /mongo-init/cfg-init.js
docker exec -i mongo1 mongosh --host mongo1 --port 27018 --file /mongo-init/rs-init.js

docker compose restart mongos

docker exec -i mongos mongosh --port 27020 --file /mongo-init/sharding.js

docker exec -i mongos mongosh --port 27020
sh.status()
db.tenant_data.getShardDistribution()

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
        "tenantId": "Alibaba_GPU"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/alibaba/clusterdata/refs/heads/master/cluster-trace-gpu-v2023/csv/openb_pod_list_multigpu50.csv",
        "tenantId": "Alibaba_MultiGPU50"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/alibaba/clusterdata/refs/heads/master/cluster-trace-gpu-v2023/csv/openb_pod_list_multigpu40.csv",
        "tenantId": "Alibaba_MultiGPU40"
        }'

curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/Azure/AzurePublicDataset/refs/heads/master/data/AzureLLMInferenceTrace_code.csv",
        "tenantId": "Azure"
        }'

curl "http://localhost:5001/data?tenantId=Azure&limit=5"

docker logs mysimbdp-coredms

docker compose down -v