rs.initiate({
  _id: "cfg",
  configsvr: true,
  members: [
    { _id: 0, host: "mongo-configsvr1:27019" },
    { _id: 1, host: "mongo-configsvr2:27019" },
    { _id: 2, host: "mongo-configsvr3:27019" }
  ]
})
