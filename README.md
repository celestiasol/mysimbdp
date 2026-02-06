# MySIMBDP Platform Setup & Usage

This guide reproduces the full `mysimbdp` platform including **MongoDB sharding**, **CoreDMS**, and **DataIngest** services.

---

## Prerequisites

* Docker & Docker Compose installed
* Internet access (for downloading datasets)
* Ports 27018, 27019, 27020, 5001, 6000 available on host

---

## 1. Start the platform

Build and start all containers:

```bash
docker-compose up --build
```

---

## 2. Initialize MongoDB config servers

```bash
docker exec -i mongo-configsvr1 mongosh --port 27019 --file /mongo-init/cfg-init.js
```

---

## 3. Initialize shard replica set

```bash
docker exec -i mongo1 mongosh --host mongo1 --port 27018 --file /mongo-init/rs-init.js
```

---

## 4. Restart Mongos router

```bash
docker compose restart mongos
```

---

## 5. Configure sharding

```bash
docker exec -i mongos mongosh --port 27020 --file /mongo-init/sharding.js
```

---

## 6. Check cluster status

Open a Mongo shell on Mongos:

```bash
docker exec -it mongos mongosh --port 27020
```

Run:

```javascript
sh.status()
db.tenant_data.getShardDistribution()
```

---

## 7. Test service availability

Stop and start a shard node (optional):

```bash
docker stop mongo1
docker start mongo1
```

Check health endpoints:

```bash
curl http://localhost:6000
curl http://localhost:5001/health
```

---

## 8. Ingest datasets

Alibaba datasets:

```bash
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
```

Azure dataset:

```bash
curl -X POST http://localhost:6000/ingest \
  -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://raw.githubusercontent.com/Azure/AzurePublicDataset/refs/heads/master/data/AzureLLMInferenceTrace_code.csv",
        "tenantId": "Azure"
      }'
```

---

## 9. Query ingested data

Example: Get last 5 records for Azure tenant:

```bash
curl "http://localhost:5001/data?tenantId=Azure&limit=5"
```

---

## 10. Check CoreDMS logs

```bash
docker logs mysimbdp-coredms
```

---

## 11. Stop the platform

```bash
docker compose down -v
```

---

## Notes

* `sh.status()` and `db.tenant_data.getShardDistribution()` should reflect active shards and chunks.
* If a shard is down, CoreDMS may temporarily fail until it reconnects.
* Ingested datasets are stored in sharded collections with `tenantId` as shard key.
* `run.sh` file is just a text file to store all the commands used to test this platform and it is not suggested to run the file as the commands there ares not structured to be run together sequentially.
