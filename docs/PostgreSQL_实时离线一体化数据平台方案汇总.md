# PostgreSQL 实时离线一体化数据平台方案

整合版：包含原始方案及基于现有环境的调整

## 一、技术架构

### 1.1 核心组件选型

数据库：PostgreSQL（已有本地数据库）

CDC方案：Debezium Embedded + PostgreSQL WAL Logical Replication

消息队列：Apache Kafka

实时计算：Spring Boot 3 + Java 21（替代Flink Runtime）

实时分析：Apache Doris

缓存服务：Redis

离线计算：Apache Spark

数据湖存储：Apache Iceberg + RustFS（S3兼容，已有）

BI可视化：Apache Superset

### 1.2 数据架构

实时数据流：

- PostgreSQL（订单表等业务数据）
- → Debezium Embedded 捕获 WAL 变更
- → Kafka Topic
- → Spring Boot 实时计算服务
- → Doris 实时指标表
- → Superset BI和大屏

离线数据流：

- PostgreSQL → Debezium → Kafka → Spark
- → Iceberg（ODS/DWD/DWS/ADS分层）
- → RustFS 对象存储

## 三、离线数仓设计

采用经典分层架构：

ODS：保存原始业务数据

DWD：清洗、标准化后的明细数据

DWS：主题汇总指标

ADS：面向报表和应用的数据

存储格式：Iceberg / Parquet

存储后端：RustFS（S3兼容对象存储）

## 四、推荐系统方案

### 4.1 MVP方案（第一阶段）

不直接建设复杂深度学习系统，采用轻量级方案：

- 用户行为采集 → Kafka
- 实时计算服务 → 用户画像计算
- Redis → 用户画像/推荐特征缓存
- Spring Boot 推荐接口

### 4.2 支持的推荐算法

- 热门推荐
- 协同过滤
- 基于标签推荐

### 4.3 后续扩展方向

- Feature Store
- Two Tower
- DeepFM

## 五、实施路线

阶段1：完成 PostgreSQL → Debezium Embedded → Kafka → Java实时服务 → Doris 链路

阶段2：建设 Spark + Iceberg + RustFS 离线数仓（ODS/DWD/DWS/ADS）

阶段3：建设 Redis 用户画像和推荐服务

阶段4：根据实时计算复杂度评估是否引入 Flink Runtime

## 六、Docker部署组件

### 需要部署

- Kafka
- Doris FE
- Doris BE
- Redis
- Spark
- Superset

### 不需要部署（已有或替代）

- PostgreSQL（本地已有）
- MinIO/RustFS（本地已有 RustFS）
- Debezium Connect（使用 Embedded 版本）
- Flink Runtime（使用 Java 自定义服务）

## 七、最终架构

完整技术栈：

- PostgreSQL（数据库）
- Debezium Embedded（CDC）
- Kafka（消息队列）
- Spring Boot（实时计算）
- Apache Doris（实时分析）
- Apache Spark（离线计算）
- Apache Iceberg（数据湖）
- RustFS（S3存储）
- Redis（缓存）
- Superset（BI可视化）

该方案满足个人资源部署条件，同时保留企业级演进路线。
