import redis
redis_url="redis://127.0.0.1:6379"
# 1.连接库
redis_client=redis.Redis.from_url(redis_url,encoding="utf-8",decode_responses=True)
# decode_responses=True告诉客户端，读取数据自动解析成字符巾

# 2.增删改查 服务端redis-server.exe记得开启
redis_client.set("test","test")
# 设置1分钟有效期
redis_client.set("code1","1234",60)

data=redis_client.get("code1")
print(data)
is_exist=redis_client.exists("code1")
print(is_exist)
redis_client.delete("code1")
is_exist=redis_client.exists("code1")
print(is_exist)
# 关闭
redis_client.close()
