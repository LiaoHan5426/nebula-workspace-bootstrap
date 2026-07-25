import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Divider,
  Grid,
  H1,
  H2,
  H3,
  Pill,
  Row,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

type ModKind = "CORE" | "OPTIONAL" | "FEATURE" | "PLUGIN" | "ORPHAN" | "DEMO";

type Mod = {
  name: string;
  role: string;
  kind: ModKind;
  note?: string;
};

function kindLabel(kind: ModKind): string {
  return kind;
}

function ModTable({ modules }: { modules: Mod[] }) {
  return (
    <Table
      headers={["Module", "Role", "Kind", "Note"]}
      columnAlign={["left", "left", "left", "left"]}
      rows={modules.map((m) => [
        m.name,
        m.role,
        kindLabel(m.kind),
        m.note ?? "—",
      ])}
      rowTone={modules.map((m) =>
        m.kind === "ORPHAN"
          ? "danger"
          : m.kind === "OPTIONAL"
            ? "warning"
            : m.kind === "FEATURE"
              ? "info"
              : undefined,
      )}
    />
  );
}

const foundation: Mod[] = [
  { name: "nebula-bom", role: "统一依赖版本 BOM", kind: "CORE" },
  { name: "nebula-tools", role: "纯工具库（无 Spring）", kind: "CORE" },
];

const integration: Mod[] = [
  {
    name: "integration-redis",
    role: "Redis / Redisson 连接",
    kind: "FEATURE",
    note: "nebula.redis.enabled",
  },
  {
    name: "integration-s3",
    role: "S3 客户端 + 健康检查",
    kind: "FEATURE",
    note: "nebula.integration.s3.enabled",
  },
  {
    name: "integration-kafka",
    role: "Kafka 工厂 + 健康检查",
    kind: "FEATURE",
    note: "nebula.integration.kafka.enabled",
  },
  {
    name: "integration-mail",
    role: "JavaMailSender + 健康检查",
    kind: "FEATURE",
    note: "nebula.integration.mail.enabled",
  },
];

const capability: Mod[] = [
  {
    name: "capability-cache",
    role: "Caffeine / Redis 缓存",
    kind: "FEATURE",
    note: "nebula.redis.kv/cache.enabled",
  },
  {
    name: "capability-lock",
    role: "分布式锁",
    kind: "FEATURE",
    note: "nebula.redis.lock.*",
  },
  {
    name: "capability-storage",
    role: "本地 / S3 文件存储",
    kind: "OPTIONAL",
    note: "应用按需引入",
  },
  {
    name: "capability-log",
    role: "组件日志",
    kind: "FEATURE",
    note: "nebula.log.enabled",
  },
  {
    name: "capability-audit",
    role: "审计 SPI / 监听",
    kind: "FEATURE",
    note: "nebula.log.audit.enabled",
  },
  {
    name: "capability-encrypt",
    role: "Jasypt 加解密",
    kind: "FEATURE",
    note: "profile config-encrypt",
  },
  {
    name: "capability-message",
    role: "内存 / Kafka 消息",
    kind: "OPTIONAL",
    note: "classpath 门控",
  },
  {
    name: "capability-notification",
    role: "站内 / Webhook / 邮件",
    kind: "OPTIONAL",
  },
  {
    name: "capability-websocket",
    role: "WebSocket",
    kind: "FEATURE",
    note: "nebula.websocket.enabled",
  },
];

const infra: Mod[] = [
  { name: "runtime-core", role: "统一响应 / 异常 / WebMvc", kind: "CORE" },
  {
    name: "runtime-context",
    role: "租户 / 安全 / 链路上下文",
    kind: "CORE",
    note: "骨架偏多",
  },
  { name: "runtime-event", role: "平台事件定义与发布", kind: "CORE" },
  {
    name: "runtime-lifecycle",
    role: "生命周期回调 SPI",
    kind: "CORE",
    note: "骨架",
  },
  {
    name: "runtime-extension",
    role: "ExtensionPoint 注册表",
    kind: "CORE",
    note: "骨架",
  },
  { name: "runtime-starter", role: "运行时聚合 Starter", kind: "CORE" },
  {
    name: "database-core",
    role: "多数据源 / Flyway / SQL 监控",
    kind: "FEATURE",
    note: "nebula.database / flyway",
  },
  {
    name: "adapter-postgres",
    role: "PostgreSQL 方言适配",
    kind: "CORE",
    note: "生产默认",
  },
  { name: "adapter-mysql", role: "MySQL 方言适配", kind: "OPTIONAL" },
  {
    name: "database-mybatis",
    role: "MyBatis 集成",
    kind: "CORE",
    note: "@ConditionalOnClass",
  },
  {
    name: "database-jpa",
    role: "JPA 集成",
    kind: "OPTIONAL",
    note: "classpath 门控",
  },
  { name: "database-starter", role: "数据库聚合 Starter", kind: "CORE" },
  { name: "security-core", role: "安全核心", kind: "CORE" },
  { name: "security-context", role: "安全上下文", kind: "CORE" },
  { name: "security-authorization", role: "授权决策", kind: "CORE" },
  { name: "security-domain", role: "RBAC 域模型", kind: "CORE" },
  { name: "security-web", role: "安全 Web 过滤", kind: "CORE" },
  {
    name: "security-session",
    role: "Session 认证",
    kind: "FEATURE",
    note: "auth-type=session",
  },
  {
    name: "security-token",
    role: "JWT 认证",
    kind: "FEATURE",
    note: "auth-type=token",
  },
  {
    name: "security-oauth2",
    role: "OAuth2",
    kind: "FEATURE",
    note: "oauth.store-type",
  },
  { name: "security-starter", role: "安全聚合 Starter", kind: "CORE" },
];

const platformModel: Mod[] = [
  { name: "resource-*", role: "统一资源抽象 / 注册 / 查询", kind: "CORE" },
  {
    name: "governance-*",
    role: "申请 / 审批 / 策略 / 审计",
    kind: "CORE",
  },
  {
    name: "version-control-*",
    role: "快照 / 差异 / 回滚",
    kind: "CORE",
  },
  { name: "release-*", role: "发布流程 / 部署目标", kind: "CORE" },
];

const platformDomains: Mod[] = [
  {
    name: "config-*",
    role: "动态配置 / CORS / CSP",
    kind: "FEATURE",
    note: "storage=jdbc",
  },
  {
    name: "task-*",
    role: "Cron / 触发 / 调度 / 依赖 / 分片",
    kind: "CORE",
    note: "DAG/分片未完全接通",
  },
  {
    name: "cluster-*",
    role: "节点 / 心跳 / 分片",
    kind: "OPTIONAL",
    note: "生产未装 cluster-starter",
  },
  {
    name: "subscribe-*",
    role: "主题 / 投递 / SSE / Webhook",
    kind: "CORE",
  },
  { name: "tenant-*", role: "租户上下文 / 存储", kind: "CORE" },
];

const plugin: Mod[] = [
  { name: "plugin-api / spi / sdk", role: "扩展点与插件 SDK", kind: "CORE" },
  { name: "plugin-core / runtime", role: "PF4J 内核与类加载", kind: "CORE" },
  { name: "plugin-manager / loader", role: "安装 / 卸载 / 热部署", kind: "CORE" },
  {
    name: "plugin-repository",
    role: "插件仓库 / Maven",
    kind: "FEATURE",
    note: "nebula.plugin.repository.*",
  },
  {
    name: "plugin-adaptor",
    role: "WebMvc / WebFlux 适配",
    kind: "OPTIONAL",
  },
  {
    name: "plugin-starter",
    role: "插件平台自动配置",
    kind: "FEATURE",
    note: "nebula.platform.enabled",
  },
];

const camel: Mod[] = [
  { name: "camel-core", role: "Camel 核心与路由构建", kind: "CORE" },
  { name: "camel-runtime", role: "CamelContext 生命周期", kind: "FEATURE" },
  { name: "camel-route", role: "Route 定义与管理", kind: "CORE" },
  { name: "camel-dag", role: "DAG 编排", kind: "CORE" },
  { name: "camel-sql", role: "SQL 查询自动配置", kind: "CORE" },
  { name: "camel-trigger", role: "触发源", kind: "CORE" },
  { name: "camel-console (+starter)", role: "控制面 REST", kind: "CORE" },
  { name: "camel-executor (+starter)", role: "执行面引擎", kind: "CORE" },
  { name: "camel-tenant", role: "集成域租户授权", kind: "CORE" },
  {
    name: "camel-subscribe",
    role: "库表轮询 / CDC",
    kind: "FEATURE",
    note: "debeziumEnabled 可选",
  },
  { name: "camel-metadata", role: "接口 / 连接器元数据", kind: "CORE" },
  { name: "camel-message", role: "平台通知消息", kind: "CORE" },
  { name: "camel-security", role: "限流 / 熔断 / 白名单", kind: "CORE" },
  { name: "camel-monitor", role: "监控日志", kind: "CORE" },
  { name: "camel-observability", role: "调用拓扑与追踪", kind: "CORE" },
  {
    name: "camel-plugin / api / sdk",
    role: "连接器插件宿主",
    kind: "PLUGIN",
  },
  {
    name: "builtin-plugin-http",
    role: "内置 HTTP 连接器",
    kind: "PLUGIN",
    note: "provided → plugins/",
  },
  {
    name: "builtin-plugin-mysql",
    role: "内置 MySQL 连接器",
    kind: "PLUGIN",
  },
  {
    name: "builtin-plugin-postgre",
    role: "内置 PostgreSQL 连接器",
    kind: "PLUGIN",
  },
  { name: "camel-starter", role: "Camel 最小 Starter", kind: "CORE" },
];

const business: Mod[] = [
  { name: "system-app", role: "应用管理", kind: "CORE" },
  { name: "system-user", role: "用户管理", kind: "CORE" },
  { name: "system-organization", role: "组织架构", kind: "CORE" },
  {
    name: "system-user-organization",
    role: "用户-组织关联",
    kind: "OPTIONAL",
    note: "未进 system-starter",
  },
  { name: "system-config", role: "系统配置", kind: "CORE" },
  { name: "system-log", role: "系统日志", kind: "CORE" },
  { name: "system-starter", role: "系统域聚合", kind: "CORE" },
  {
    name: "module-user",
    role: "用户 REST 门面",
    kind: "OPTIONAL",
    note: "console 已引入",
  },
  {
    name: "module-organization",
    role: "组织 REST 门面",
    kind: "OPTIONAL",
    note: "console 已引入",
  },
  {
    name: "module-config",
    role: "业务配置 REST",
    kind: "OPTIONAL",
    note: "生产未引入",
  },
  {
    name: "module-tenant-extension",
    role: "租户业务扩展 REST",
    kind: "OPTIONAL",
    note: "生产未引入",
  },
  { name: "module-file", role: "文件管理 REST", kind: "CORE" },
];

const apps: Mod[] = [
  {
    name: "platform-console",
    role: "应用中台 :8090",
    kind: "CORE",
    note: "system + governance + modules",
  },
  {
    name: "platform-integration",
    role: "集成控制面 :8080",
    kind: "CORE",
    note: "camel-console-starter",
  },
  {
    name: "platform-integration-executor",
    role: "集成执行器 :8081",
    kind: "CORE",
    note: "camel-executor-starter",
  },
  {
    name: "platform-admin",
    role: "旧管理入口",
    kind: "ORPHAN",
    note: "有代码，未进父 POM",
  },
  { name: "demos/*", role: "演示 / 示例插件", kind: "DEMO" },
];

const layers = [
  {
    layer: "L7 应用层",
    items:
      "console :8090 · integration :8080 · executor :8081 · demos · platform-admin(ORPHAN)",
  },
  {
    layer: "L6 业务层",
    items: "nebula-system · nebula-modules（可插拔 REST）",
  },
  {
    layer: "L5 平台域",
    items:
      "resource → governance → version → release · config/task/cluster/subscribe/tenant · plugin · camel",
  },
  {
    layer: "L4 基础设施",
    items: "runtime · database · security",
  },
  {
    layer: "L3 能力层",
    items:
      "cache · lock · storage · log · audit · encrypt · message · notification · websocket",
  },
  {
    layer: "L2 集成层",
    items: "redis · s3 · kafka · mail（仅连接，无业务语义）",
  },
  {
    layer: "L1 基础",
    items: "nebula-bom · nebula-tools · Spring Boot / Camel / MyBatis / PF4J",
  },
];

export default function NebulaBackendModuleArchitecture() {
  const theme = useHostTheme();

  const all = [
    ...foundation,
    ...integration,
    ...capability,
    ...infra,
    ...platformModel,
    ...platformDomains,
    ...plugin,
    ...camel,
    ...business,
    ...apps,
  ];
  const optionalCount = all.filter((m) =>
    ["OPTIONAL", "FEATURE", "PLUGIN", "ORPHAN"].includes(m.kind),
  ).length;

  return (
    <Stack gap={24} style={{ padding: 24 }}>
      <Stack gap={8}>
        <H1>Nebula 后端完整模块架构</H1>
        <Text tone="secondary">
          Maven 多模块 + Spring Conditional +
          PF4J。可选模块 = 依赖装配 + property/classpath 门控 +
          插件热加载。用于制定开发 / 重构计划。
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value={String(all.length)} label="清单条目（含子模块聚合）" />
        <Stat
          value={String(optionalCount)}
          label="OPTIONAL / FEATURE / PLUGIN / ORPHAN"
          tone="warning"
        />
        <Stat value="3" label="生产进程入口" tone="success" />
        <Stat value="7" label="架构分层" />
      </Grid>

      <Callout tone="info" title="门控方式（无 Cargo features）">
        Maven 依赖决定 classpath → AutoConfiguration.imports →
        @ConditionalOnProperty / OnClass → PF4J plugins/
        热加载。未引入的模块不会进入生产二进制。
      </Callout>

      <H2>分层总览（上依赖下）</H2>
      <Stack gap={8}>
        {layers.map((row) => (
          <div
            key={row.layer}
            style={{
              padding: "10px 12px",
              borderWidth: 1,
              borderStyle: "solid",
              borderColor: theme.stroke.secondary,
              borderRadius: 6,
              background: theme.fill.tertiary,
              display: "flex",
              gap: 12,
              alignItems: "center",
            }}
          >
            <Text weight="semibold" style={{ minWidth: 110 }}>
              {row.layer}
            </Text>
            <Text tone="secondary" size="small">
              {row.items}
            </Text>
          </div>
        ))}
      </Stack>

      <H2>图例</H2>
      <Row gap={8} wrap>
        <Pill size="sm" active>
          CORE
        </Pill>
        <Text size="small">主干 / 生产装配</Text>
        <Pill size="sm">OPTIONAL</Pill>
        <Text size="small">可选依赖</Text>
        <Pill size="sm">FEATURE</Pill>
        <Text size="small">property / classpath 开关</Text>
        <Pill size="sm">PLUGIN</Pill>
        <Text size="small">PF4J 运行时</Text>
        <Pill size="sm">ORPHAN</Pill>
        <Text size="small">代码在、聚合缺失</Text>
        <Pill size="sm">DEMO</Pill>
        <Text size="small">演示非生产</Text>
      </Row>

      <Divider />

      <H2>L7 平台应用</H2>
      <Text tone="secondary" size="small">
        nebula-platform / demos — 生产三条进程边界
      </Text>
      <ModTable modules={apps} />

      <H2>L6 业务层</H2>
      <Text tone="secondary" size="small">
        nebula-system + nebula-modules
      </Text>
      <ModTable modules={business} />

      <H2>L5 平台域 — 核心模型闭环</H2>
      <Text tone="secondary" size="small">
        Resource → Governance → Version → Release →
        Runtime（Deploy→Runtime 生效仍需关口验收）
      </Text>
      <ModTable modules={platformModel} />

      <H2>L5 平台域 — 能力域</H2>
      <ModTable modules={platformDomains} />

      <H2>L5 平台域 — 插件平台</H2>
      <Text tone="secondary" size="small">
        Extension SPI：Menu / Permission / Audit / Workflow / SecurityPolicy /
        CamelConnector
      </Text>
      <ModTable modules={plugin} />

      <H2>L5 平台域 — Camel 企业集成</H2>
      <ModTable modules={camel} />

      <H2>L4 基础设施</H2>
      <ModTable modules={infra} />

      <H2>L3 能力层</H2>
      <ModTable modules={capability} />

      <H2>L2 集成层</H2>
      <ModTable modules={integration} />

      <H2>L1 基础</H2>
      <ModTable modules={foundation} />

      <Divider />

      <H2>生产装配对照</H2>
      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader>platform-console :8090</CardHeader>
          <CardBody>
            <Stack gap={6}>
              <Text size="small">
                system-starter · governance · config · resource · release ·
                version · module-user/org/file · security(session+token) ·
                task · subscribe · plugin · 部分 capability/integration ·
                camel-observability
              </Text>
              <Text tone="secondary" size="small">
                不直接依赖 camel-console
              </Text>
            </Stack>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>platform-integration :8080</CardHeader>
          <CardBody>
            <Text size="small">
              camel-console-starter · camel-runtime/observability · plugin ·
              部分 system · governance/release/version/resource · task ·
              builtin plugins(provided)
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader>platform-integration-executor :8081</CardHeader>
          <CardBody>
            <Text size="small">
              camel-executor-starter · camel-runtime/observability · plugin ·
              release · task · cluster-core（非 starter）· builtin plugins
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <H2>重构 / 开发计划热点</H2>
      <Grid columns={2} gap={12}>
        <Card>
          <CardHeader trailing={<Pill size="sm" active>优先</Pill>}>
            文档 ↔ 代码漂移
          </CardHeader>
          <CardBody>
            <Table
              headers={["项", "状态 / 建议"]}
              rows={[
                [
                  "platform-admin",
                  "待处理：删除或重新纳入聚合 / 文档标注遗留",
                ],
                [
                  "module-config / tenant-extension",
                  "待处理：接入 console 或移出正式 modules 树",
                ],
                [
                  "system-user-organization",
                  "待处理：并入 system-starter 或明确按需依赖",
                ],
                [
                  "cluster-starter",
                  "待处理：接入 executor 或降级为实验模块",
                ],
                [
                  "system-config-encrypt（文档）",
                  "已纠偏 → capability-encrypt",
                ],
                [
                  "旧 nebula-module-dag/flow/…",
                  "已纠偏 → camel-dag / governance-workflow / cluster / task / capability-message / version-control",
                ],
              ]}
            />
          </CardBody>
        </Card>
        <Card>
          <CardHeader>能力闭环缺口</CardHeader>
          <CardBody>
            <Table
              headers={["链路", "状态提示"]}
              rows={[
                [
                  "Resource→…→Release",
                  "API 有；Deploy→Runtime 需验收",
                ],
                [
                  "task-dependency / task-cluster",
                  "代码有；主路径未完全接通",
                ],
                ["CDC Debezium", "可降级 Simulated；生产策略待定"],
                [
                  "runtime-context/lifecycle/extension",
                  "骨架，需收敛",
                ],
                [
                  "plugin 远程仓库 / 市场 API",
                  "仓库有；市场仍偏演示",
                ],
                [
                  "adapter-oracle / nebula-ai",
                  "文档或 BOM 有；模块未建",
                ],
              ]}
            />
          </CardBody>
        </Card>
      </Grid>

      <H2>建议的计划切片顺序</H2>
      <Stack gap={10}>
        <H3>Wave A — 边界与清单收敛</H3>
        <Text size="small">
          清理 ORPHAN / 未装配 OPTIONAL；统一文档模块树；明确三条进程依赖矩阵。
        </Text>
        <H3>Wave B — 平台核心闭环</H3>
        <Text size="small">
          打通 Release→Runtime；补齐 Resource/Governance E2E 与持久化一致性。
        </Text>
        <H3>Wave C — 调度与集群</H3>
        <Text size="small">
          接通 task DAG / 分片；决定 cluster-starter 是否进入生产装配。
        </Text>
        <H3>Wave D — 集成数据面增强</H3>
        <Text size="small">
          CDC 生产策略、observability、builtin 连接器与远程插件仓库。
        </Text>
        <H3>Wave E — 可选能力产品化</H3>
        <Text size="small">
          按需产品化 module-config / tenant-extension / notification /
          websocket / JPA / MySQL adapter。
        </Text>
      </Stack>

      <Text tone="tertiary" size="small">
        源：nebula/docs/architecture.md · development-status.md · 仓库 pom
        实勘。叶子 artifact 以全部 pom.xml 为准（约 130+）。
      </Text>
    </Stack>
  );
}
