sh.addShard("rs0/mongo1:27018,mongo2:27018,mongo3:27018");

sh.enableSharding("mysimbdp");

sh.shardCollection(
  "mysimbdp.tenant_data",
  { tenantId: "hashed" }
);
