# MaxKB on Windows (WSL) 排错

## 当前问题

`docker.service failed` + `Cannot connect to docker.sock`

原因：MaxKB 离线包自带 Docker，在 **WSL2** 上常因 **iptables/nftables** 无法启动。

---

## 方案 A：修复 WSL 自带 Docker（先试）

Ubuntu 终端：

```bash
bash /mnt/c/Users/alu/Desktop/TRANSWING/tools/fix_maxkb_docker.sh
```

或手动：

```bash
sudo mkdir -p /etc/docker
sudo tee /etc/docker/daemon.json <<'EOF'
{
  "iptables": false,
  "ip-masq": false
}
EOF

sudo systemctl daemon-reload
sudo systemctl restart docker
sudo docker info
sudo mkctl reload
```

---

## 方案 B：Docker Desktop（Windows 上最稳，推荐）

1. 安装 [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop/)
2. 打开 Docker Desktop → **Settings → Resources → WSL integration** → 勾选 **Ubuntu**
3. 确保 Docker Desktop 托盘图标为 Running
4. WSL 里验证：

```bash
docker info
sudo mkctl reload
sudo mkctl status
```

5. 浏览器：`http://localhost:8080`

> MaxKB 离线安装的 `/usr/bin/docker` 会连到同一 `docker.sock`，一般可与 Docker Desktop 共用。

---

## maxkb 容器 Restarting + `Temporary failure in name resolution`

**真实原因（MaxKB v2.8+ 常见）**：镜像内置沙箱变量

```text
MAXKB_SANDBOX_PYTHON_BANNED_HOSTS=...,maxkb,pgsql,redis,172.31.250.192/26,...
```

- `MAXKB_DB_HOST=pgsql` → 主机名在禁止名单
- 即使用 IP `172.31.250.x` → 整个 `172.31.250.192/26` 网段也被 ban
- 启动时 Django migrate 连库失败 → 容器 crash loop

**这不是单纯 WSL DNS 问题，是沙箱误伤 compose 内网 DB。**

### 正确修复（推荐）

编辑 `/opt/maxkb/conf/maxkb.env`，在末尾追加（或写入 docker-compose maxkb 的 environment）：

```bash
sudo tee -a /opt/maxkb/conf/maxkb.env <<'EOF'
MAXKB_SANDBOX_PYTHON_BANNED_HOSTS=127.0.0.0/8,localhost,host.docker.internal,172.17.0.0/16
EOF

# 改回 Docker 内网主机名（不要用 IP）
sudo sed -i 's/^MAXKB_DB_HOST=.*/MAXKB_DB_HOST=pgsql/' /opt/maxkb/conf/maxkb.env
sudo sed -i 's/^MAXKB_REDIS_HOST=.*/MAXKB_REDIS_HOST=redis/' /opt/maxkb/conf/maxkb.env

sudo mkctl restart maxkb
sleep 30
sudo mkctl status
curl -I http://127.0.0.1:8080
```

说明：从 ban list 中 **去掉 `pgsql`、`redis`、`172.31.250.192/26`**，保留对 localhost/元数据等 SSRF 防护。

### 旧方案：Docker iptables（仍可能需要）

WSL 上 Docker 若起不来，仍需 `daemon.json` 里 `"iptables": false`（见上文方案 A）。

---

```bash
sudo journalctl -u docker --no-pager -n 50
sudo /usr/bin/dockerd
```

把最后 20 行贴出来。

---

## 方案 C：放弃 WSL 离线包，改用纯 Docker 命令

若 A/B 都麻烦，可卸载离线 Docker 冲突后只用 Docker Desktop：

```bash
sudo mkctl uninstall   # 仅卸 MaxKB 容器，保留数据需先备份 /opt/maxkb
```

然后用官方一行命令（Docker Desktop 已运行时）：

```powershell
docker run -d --name=maxkb --restart=always -p 8080:8080 -v C:/maxkb:/var/lib/postgresql/data -v C:/python-packages:/opt/maxkb/app/sandbox/python-packages registry.fit2cloud.com/maxkb/maxkb
```

（需能拉镜像；离线环境则继续修方案 A）

---

## 登录

- URL: http://localhost:8080
- 用户: admin
- 密码: MaxKB@123..
