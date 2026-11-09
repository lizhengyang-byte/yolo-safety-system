<template>
  <div class="mail-report">
    <el-alert
      class="tip"
      type="info"
      :closable="false"
      show-icon
      title="预警与报告邮件配置"
      description="在这里配置 SMTP 邮件服务器、预警邮件开关，以及日报/周报的定时发送。保存后立即生效，无需重启后端。"
    />

    <el-row :gutter="16">
      <el-col :xs="24" :lg="14">
        <el-card class="cfg-card">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><Message /></el-icon></span>
              邮件服务器（SMTP）
              <el-tag v-if="mailConfigured" type="success" effect="plain" size="small">已配置</el-tag>
              <el-tag v-else type="warning" effect="plain" size="small">未配置</el-tag>
            </div>
          </template>

          <el-form :model="mail" label-width="112px" v-loading="loadingMail">
            <el-form-item label="启用邮件通知">
              <el-switch v-model="mail.enabled" />
              <span class="inline-hint">关闭后预警邮件与报告邮件都不发送</span>
            </el-form-item>
            <el-form-item label="SMTP 服务器">
              <el-input v-model="mail.host" placeholder="如 smtp.example.com" clearable />
            </el-form-item>
            <el-form-item label="端口">
              <el-input-number v-model="mail.port" :min="1" :max="65535" controls-position="right" style="width: 180px" />
            </el-form-item>
            <el-form-item label="加密方式">
              <el-radio-group v-model="secureMode">
                <el-radio-button label="ssl">SSL（465）</el-radio-button>
                <el-radio-button label="starttls">STARTTLS（587）</el-radio-button>
                <el-radio-button label="none">无</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="账号">
              <el-input v-model="mail.user" placeholder="登录账号，如 alert@example.com" clearable />
            </el-form-item>
            <el-form-item label="密码/授权码">
              <el-input
                v-model="mail.password"
                type="password"
                show-password
                :placeholder="mail.has_password ? '已保存，留空则不修改' : '请输入邮箱授权码'"
              />
            </el-form-item>
            <el-form-item label="发件人">
              <el-input v-model="mail.from" placeholder="留空默认使用账号" clearable />
            </el-form-item>
            <el-form-item label="收件人">
              <el-input v-model="mail.to" placeholder="多个收件人用英文逗号分隔" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingMail" @click="saveMail">保存配置</el-button>
              <el-button :loading="testing" @click="onTest">
                <el-icon class="btn-ico"><Promotion /></el-icon>发送测试邮件
              </el-button>
            </el-form-item>
          </el-form>

          <div class="hint-line">
            提示：QQ / 163 邮箱请填写「授权码」而非登录密码；保存后点「发送测试邮件」即可验证。
            邮件中的抓拍图为该摄像头/类型最近一条违规证据图。
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="10">
        <el-card class="cfg-card">
          <template #header>
            <div class="card-head-title">
              <span class="ico"><el-icon><Calendar /></el-icon></span>
              报告邮件推送
            </div>
          </template>

          <el-form :model="report" label-width="104px" v-loading="loadingReport">
            <el-form-item label="预警邮件">
              <el-switch v-model="report.warning_email_enabled" />
              <span class="inline-hint">违规触发预警时立即发送</span>
            </el-form-item>
            <el-divider content-position="left">定时报告</el-divider>
            <el-form-item label="日报">
              <el-switch v-model="report.daily_enabled" />
              <el-time-picker
                v-model="report.daily_time"
                value-format="HH:mm"
                format="HH:mm"
                placeholder="08:30"
                :disabled="!report.daily_enabled"
                style="width: 120px; margin-left: 12px"
              />
            </el-form-item>
            <el-form-item label="周报">
              <el-switch v-model="report.weekly_enabled" />
              <el-select
                v-model="report.weekly_day"
                :disabled="!report.weekly_enabled"
                style="width: 96px; margin-left: 12px"
              >
                <el-option v-for="d in weekDays" :key="d.value" :label="d.label" :value="d.value" />
              </el-select>
              <el-time-picker
                v-model="report.weekly_time"
                value-format="HH:mm"
                format="HH:mm"
                placeholder="09:00"
                :disabled="!report.weekly_enabled"
                style="width: 120px; margin-left: 8px"
              />
            </el-form-item>
            <el-form-item label="报告收件人">
              <el-input v-model="report.report_to" placeholder="留空则使用上面的收件人" clearable />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingReport" @click="saveReport">保存推送设置</el-button>
            </el-form-item>
          </el-form>

          <el-divider content-position="left">立即发送</el-divider>
          <div class="manual-actions">
            <el-button size="small" :loading="sending === 'daily'" @click="sendNow('daily')">发送日报</el-button>
            <el-button size="small" :loading="sending === 'week'" @click="sendNow('week')">发送周报</el-button>
            <el-button size="small" :loading="sending === 'month'" @click="sendNow('month')">发送月报</el-button>
          </div>
          <div class="last-info">
            最近发送：日报 {{ report.last_daily_sent || "—" }} · 周报 {{ report.last_weekly_sent || "—" }}
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { ElMessage } from "element-plus";
import {
  getMailConfig,
  getReportConfig,
  sendReportNow,
  testMail,
  updateMailConfig,
  updateReportConfig,
  type MailConfig,
  type ReportConfig,
} from "@/api/settings";

const loadingMail = ref(false);
const loadingReport = ref(false);
const savingMail = ref(false);
const savingReport = ref(false);
const testing = ref(false);
const sending = ref<"" | "daily" | "week" | "month">("");

const mail = reactive<MailConfig>({
  enabled: true,
  host: "",
  port: 465,
  user: "",
  password: "",
  ssl: true,
  starttls: false,
  from: "",
  to: "",
  has_password: false,
});

const report = reactive<ReportConfig>({
  warning_email_enabled: true,
  daily_enabled: false,
  daily_time: "08:30",
  weekly_enabled: false,
  weekly_day: 1,
  weekly_time: "09:00",
  report_to: "",
  last_daily_sent: "",
  last_weekly_sent: "",
});

const weekDays = [
  { value: 1, label: "周一" },
  { value: 2, label: "周二" },
  { value: 3, label: "周三" },
  { value: 4, label: "周四" },
  { value: 5, label: "周五" },
  { value: 6, label: "周六" },
  { value: 7, label: "周日" },
];

const secureMode = computed({
  get: () => (mail.ssl ? "ssl" : mail.starttls ? "starttls" : "none"),
  set: (v: string) => {
    mail.ssl = v === "ssl";
    mail.starttls = v === "starttls";
    if (v === "ssl" && (!mail.port || mail.port === 587)) mail.port = 465;
    if (v === "starttls" && (!mail.port || mail.port === 465)) mail.port = 587;
  },
});

const mailConfigured = computed(() => !!mail.host && !!mail.to);

function applyMail(cfg: MailConfig) {
  Object.assign(mail, cfg);
  mail.password = ""; // 密码不回显，留空表示不修改
  mail.has_password = cfg.has_password ?? false;
}

function applyReport(cfg: ReportConfig) {
  Object.assign(report, cfg);
}

async function loadMail() {
  loadingMail.value = true;
  try {
    applyMail(await getMailConfig());
  } finally {
    loadingMail.value = false;
  }
}

async function loadReport() {
  loadingReport.value = true;
  try {
    applyReport(await getReportConfig());
  } finally {
    loadingReport.value = false;
  }
}

async function saveMail() {
  savingMail.value = true;
  try {
    const cfg = await updateMailConfig({
      enabled: mail.enabled,
      host: mail.host,
      port: mail.port,
      user: mail.user,
      password: mail.password || undefined,
      ssl: mail.ssl,
      starttls: mail.starttls,
      from: mail.from,
      to: mail.to,
    });
    applyMail(cfg);
    ElMessage.success("邮件配置已保存");
  } finally {
    savingMail.value = false;
  }
}

async function onTest() {
  testing.value = true;
  try {
    const res = await testMail();
    if (res.ok) ElMessage.success(res.message);
    else ElMessage.warning(res.message);
  } finally {
    testing.value = false;
  }
}

async function saveReport() {
  savingReport.value = true;
  try {
    const cfg = await updateReportConfig({
      warning_email_enabled: report.warning_email_enabled,
      daily_enabled: report.daily_enabled,
      daily_time: report.daily_time,
      weekly_enabled: report.weekly_enabled,
      weekly_day: report.weekly_day,
      weekly_time: report.weekly_time,
      report_to: report.report_to,
    });
    applyReport(cfg);
    ElMessage.success("报告推送设置已保存");
  } finally {
    savingReport.value = false;
  }
}

async function sendNow(period: "daily" | "week" | "month") {
  sending.value = period;
  try {
    const res = await sendReportNow(period);
    ElMessage.success(res.message);
    loadReport();
  } finally {
    sending.value = "";
  }
}

onMounted(() => {
  loadMail();
  loadReport();
});
</script>

<style scoped>
.mail-report {
  display: flex;
  flex-direction: column;
}
.tip {
  margin-bottom: 16px;
}
.cfg-card {
  height: 100%;
}
.card-head-title {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  color: var(--text-1);
}
.card-head-title .ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  background: linear-gradient(135deg, var(--brand-100), #eef4ff);
  color: var(--brand-500);
  font-size: 15px;
}
.inline-hint {
  margin-left: 10px;
  color: var(--text-3);
  font-size: 12px;
}
.hint-line {
  margin-top: 4px;
  padding: 10px 12px;
  border-radius: 8px;
  background: var(--surface-soft);
  border: 1px dashed var(--border);
  color: var(--text-3);
  font-size: 12.5px;
  line-height: 1.7;
}
.manual-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.last-info {
  margin-top: 12px;
  font-size: 12px;
  color: var(--text-3);
}
</style>
