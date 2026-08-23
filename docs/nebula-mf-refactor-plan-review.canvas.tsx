import {
  Callout,
  Card,
  CardBody,
  CardHeader,
  Grid,
  H1,
  H2,
  Pill,
  Stack,
  Stat,
  Table,
  Text,
  useHostTheme,
} from "cursor/canvas";

type Claim = {
  claim: string;
  note: string;
};

const CLAIMS: Claim[] = [
  {
    claim: "Phase 0 全部属于 [A]，且为真实 Remote 迁移前硬门槛",
    note: "§11 Phase 0 首句已写明；退出条件禁止引用 B/C，失败不得进入真实 Remote。",
  },
  {
    claim: "Phase 7 全部属于 [A]",
    note: "与 Phase 3 相同写法：「本阶段全部属于 [A]」。iframe/external、CSP、LKG、灰度均在 A 轨。",
  },
  {
    claim: "Phase 5 平台 contract 不含 Pinia/Query/i18n",
    note: "清单限定为 Host capabilities、application contract、api-client adapter；B 轨仍单独迁移 Query/Pinia/i18n。",
  },
  {
    claim: "§17 按 A 1–16、B 17–24、C 25–41 分组",
    note: "三组标题与编号连续；A 含 CSS 隔离（15–16），与上一轮建议一致。",
  },
  {
    claim: "单轨可独立验收；全路线图完成才三组同时满足",
    note: "§17 开篇已写。关闭某一轨道不等待其他轨道。",
  },
];

export default function MfRefactorPlanReview() {
  const theme = useHostTheme();

  return (
    <Stack gap={24}>
      <Stack gap={8}>
        <H1>重构计划审查（P2 勘误后）</H1>
        <Text tone="secondary">
          对象：`docs/nebula-module-federation-frontend-refactoring-plan.md`（文首仍标 v1.1）。基线
          nebula@39ca670、nebula-studio@88f0d8da。对照本轮 5 项调整复核上一轮全部 P2。
        </Text>
      </Stack>

      <Grid columns={4} gap={12}>
        <Stat value="通过" label="总体结论" tone="success" />
        <Stat value="0" label="开放 P0 / P1 / P2" />
        <Stat value="5/5" label="本轮调整已核对" tone="success" />
        <Stat value="A 轨" label="允许开工" tone="success" />
      </Grid>

      <Callout tone="success" title="没有开放审查项">
        上一轮 3 条 P2（Phase 0/7 标记、§17 未分轨、Phase 5 contract 措辞）均已写入正文。计划可以作为 A
        轨实施依据。下一步是技术验证分支，不是继续改文档。
      </Callout>

      <H2>本轮调整核对</H2>
      <Text tone="secondary" size="small">
        Source: §11 Phase 0 / Phase 5 / Phase 7 · §17 · 2026-08-22。
      </Text>
      <Table
        headers={["调整", "正文位置"]}
        rows={CLAIMS.map((c) => [c.claim, c.note])}
        rowTone={CLAIMS.map(() => "success" as const)}
        striped
      />

      <H2>轨道关门（现标准）</H2>
      <Grid columns={3} gap={12}>
        <Card>
          <CardHeader trailing={<Pill active size="sm">1–16</Pill>}>
            A 应用交付
          </CardHeader>
          <CardBody>
            <Text size="small">
              Host/Remote、registry、四种 driver、CSS 隔离。Phase 0 硬门槛通过后才能迁 Docs。不等待 B/C。
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">17–24</Pill>}>
            B 体验底座
          </CardHeader>
          <CardBody>
            <Text size="small">
              主题、patterns、Pinia、Query、i18n。可随 Remote 增量交付，不阻塞 A 轨切换制品边界。
            </Text>
          </CardBody>
        </Card>
        <Card>
          <CardHeader trailing={<Pill size="sm">25–41</Pill>}>
            C 低代码
          </CardHeader>
          <CardBody>
            <Text size="small">
              依赖已完成的 A 轨 contract/federation driver。不反向阻塞首批 Remote 上线。
            </Text>
          </CardBody>
        </Card>
      </Grid>

      <H2>建议立即执行</H2>
      <Text>
        按 §18 / Phase 0：锁定 `@module-federation/vite`、Hello Remote 双入口、Web 动态加载、Electron
        http 与 file、cssNamespace 冲突测试、双 expose chunk 图。CSS 失败则停 A 轨，不进入 Docs。
      </Text>

      <Callout tone="neutral" title="文档元数据（不开放）">
        文首版本仍为 v1.1，变更摘要未写入本轮 P2 勘误；§2.3 首段仍有一句把「成功标准」说成整份路线图最终完成标准，但
        §17 分组规则已覆盖。不构成实施缺口。
      </Callout>

      <Text tone="tertiary" size="small">
        Source: 计划正文 · nebula 39ca670 · nebula-studio 88f0d8da · 审查 2026-08-22 · 主题{" "}
        {theme.kind}
      </Text>
    </Stack>
  );
}
