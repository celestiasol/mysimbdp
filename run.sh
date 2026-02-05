docker-compose up --build
docker exec -it mongo1 mongosh < ./mongo-init/rs-init.js

docker stop mongo1
docker start mongo1

curl http://localhost:6000
curl http://localhost:5001/health

curl -X POST http://localhost:6000/ingest \           -H "Content-Type: application/json" \
  -d '{
        "dataset_url":"https://public.boxcloud.com/d/1/b1!uLkrVmRy9hqXH9RnBkTa52SLElmtSyR6_Rys7IgI_6ehcANwrgV1XuHdugy7u5-Pr0r7fIyOqNe8Pt86hX5GLth-5Xjck1RxU5SU_BuvfZxB-4qMFF7PM_T1xWu8hDNrklyzZ0XxO4fk6Q2Oo6dv5frv-vHyqWbkVv5C-16NYNNfyzI60OFDB4VVuTxEYjLsAw74VBsMmdxlKGLCSkwTPUcqid4n9llxVyAqWnw8_7ZyCuBsAhug9DbgVnHme9G6wNdrt1tgqRJeZ4im7ew8suYnvYbwLqIEYPoOiCd9BAZdGnLg6zMRR9oSpqdB6RVlighj0ojugdOnb727515zj_93D9YJ2p_m8-DC-wnzBc3dzuJKctpatHPsyfU3YLhEro-vaSOiZy6cS_upC1RePs4i3FYt3deutxrhbctFKEydMAJ4BPDLaQFye-chdzlsNPceW2uMetB_G1S3KTmiQrMvGR-XzpMl_bOKTeN9tUcx-heMPr82FwkzDufU4hOG4aiL7Xi3XVJ_55E4XyDRXrZcEIGEIefYfxGy9xKHfWAczn1PUQ8WHRda7Vaj405KAMn0kFkR34pF-Tmf2qxPBXggwrOA1P8utlGyQycSTxun2HFBcrczq4guLjtLIlvaW_gY2RNybWO7VBWBpR3HMmILe555fOzT-Oc4_r-0WC1J7NyjDPTwdMsFVHpUExH5eS76EkIIcGgWfOvYIiJnTTyArIVeVSSPHsoeR0euD6FUH2O0SR6pb-7mysd5HQukBT4dO6SSR4b3afbC83r_p1C1K-Oz8icsRhDv4JtSSm2qqyMhDUJo3HlDB7V3NIsX0K72WTL1O0umZ53O75P-iiyCLD8qW9xQqEz2Au1QJd1swpGyT0pxiwyknmEvhT6aQ-xNDQB6Cl2kSLaJedw7dLZtgEyGwCtiLOMa2cbMPjNKHM8cEvksqb2TNsrJfkjTPHwYhwD_O512QaNXH_BfzvdLWZsdUqRhwUNaWXnzPTpggB3WcECp-H4tQcEd3HxjLTdwdr6GU5IvWYXEcCLQh8W8JscCgykoBvM4laE6LRxqn1I-sc2qdcCsZd2QAF2-ceJVOXOUoQwCuYp3Knut2iyJhDuAxQrKgtmk5xEpvNsuh_2wgwBCoJ-2pMAp5S9PpbIqZT0feFXQb-DKtG-PpYfhy2pSFfeF4eWylLtg5_EtWK-u0z519ehWoA9JmJCX5bxCFPkDNyOdT4dJoF5sFZk6lHWjZ9b3X-G201eMWi5Sf1PsS9xYzNFMjIsmWi--fZzuujId59DDPY9PvYItybtjkevSkvh1S8d_ygbKohemnf67WGlReIct1auLBijzl_ohZ2HfE5tawgSJ19Quur3ieDCRuEIqHgz81DlDd_jpoQ../download",
                "tenantId": "NIH"
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