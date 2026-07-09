<template>
  <div class="page-container">
    <div class="card-box">
      <h3 class="mb-20">系统设置</h3>

      <el-tabs v-model="activeTab">
        <!-- 基本设置 -->
        <el-tab-pane label="基本设置" name="basic">
          <el-form :model="settings" label-width="140px" style="max-width: 600px;">
            <el-form-item label="支付模式">
              <el-select v-model="settings.payment_mode">
                <el-option label="模拟支付" value="mock" />
                <el-option label="真实支付" value="wechat" />
              </el-select>
              <div style="font-size: 12px; color: #909399; margin-top: 4px;">切换支付模式需要二次确认</div>
            </el-form-item>
            <el-form-item label="订单超时时间">
              <el-input-number v-model="settings.order_timeout_minutes" :min="10" :max="120" />
              <span style="margin-left: 8px; color: #909399;">分钟</span>
            </el-form-item>
            <el-form-item label="库存告警阈值">
              <el-input-number v-model="settings.stock_alert_threshold" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="二次确认机制">
              <el-switch v-model="settings.enable_confirm" />
              <span style="margin-left: 8px; color: #909399;">强烈建议保持开启</span>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSave">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 退票规则 -->
        <el-tab-pane label="退票规则" name="refund">
          <el-form :model="settings" label-width="140px" style="max-width: 600px;">
            <el-form-item label="允许退票">
              <el-switch v-model="settings.allow_refund" />
            </el-form-item>
            <el-form-item label="退票截止时间">
              <el-input-number v-model="settings.refund_deadline_hours" :min="0" />
              <span style="margin-left: 8px; color: var(--color-text-placeholder);">使用日期前N小时</span>
            </el-form-item>
            <el-form-item label="退票手续费(%)">
              <el-input-number v-model="settings.refund_fee_rate" :min="0" :max="100" :step="5" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSave">保存设置</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 客服设置 -->
        <el-tab-pane label="客服设置" name="customer">
          <el-form :model="csConfig" label-width="120px" style="max-width: 600px;">
            <el-form-item label="客服电话">
              <el-input v-model="csConfig.phone" placeholder="如: 400-xxx-xxxx" />
            </el-form-item>
            <el-form-item label="客服微信号">
              <el-input v-model="csConfig.wechat" placeholder="微信号" />
            </el-form-item>
            <el-form-item label="工作时间">
              <el-input v-model="csConfig.work_hours" placeholder="如: 09:00-18:00" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="handleSaveCS">保存</el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 操作密码 -->
        <el-tab-pane v-if="userStore.isSuperAdmin" label="操作密码" name="operation">
          <el-form :model="operationPasswordForm" label-width="140px" style="max-width: 600px;">
            <el-alert
              class="mb-20"
              title="操作密码当前用于财务出账、含敏感客户信息的订单导出；如后续接入批量删除商品或订单，也必须使用操作密码。已有操作密码时需输入旧密码后才能修改。"
              type="warning"
              :closable="false"
            />
            <el-form-item label="旧操作密码">
              <el-input
                v-model="operationPasswordForm.oldPassword"
                type="password"
                maxlength="6"
                inputmode="numeric"
                pattern="[0-9]*"
                show-password
                placeholder="首次设置可留空"
              />
            </el-form-item>
            <el-form-item label="六位数字密码">
              <el-input
                v-model="operationPasswordForm.password"
                type="password"
                maxlength="6"
                inputmode="numeric"
                pattern="[0-9]*"
                show-password
                placeholder="请输入6位数字"
              />
            </el-form-item>
            <el-form-item label="再次输入">
              <el-input
                v-model="operationPasswordForm.confirmPassword"
                type="password"
                maxlength="6"
                inputmode="numeric"
                pattern="[0-9]*"
                show-password
                placeholder="请再次输入"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="savingOperationPassword" @click="handleSaveOperationPassword">
                保存操作密码
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 免责声明 -->
        <el-tab-pane label="免责声明" name="disclaimer">
          <div v-for="tpl in disclaimerTemplates" :key="tpl.id" class="mb-20">
            <h4 class="mb-8">模板 #{{ tpl.id }}</h4>
            <el-input v-model="tpl.content" type="textarea" :rows="8" />
            <el-button type="primary" size="small" class="mt-8" @click="handleSaveDisclaimer(tpl)">保存</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getSettings, updateSettings, updateCustomerServiceConfig, getDisclaimerTemplates, updateDisclaimerTemplate, updateOperationPassword } from '@/api/system'
import { useUserStore } from '@/stores/user'

const activeTab = ref('basic')
const userStore = useUserStore()

const settings = reactive({
  payment_mode: 'mock',
  order_timeout_minutes: 30,
  stock_alert_threshold: 5,
  enable_confirm: true,
  allow_refund: true,
  refund_deadline_hours: 24,
  refund_fee_rate: 10,
})

const csConfig = reactive({ phone: '', wechat: '', work_hours: '' })
const disclaimerTemplates = ref<any[]>([])
const operationPasswordForm = reactive({ oldPassword: '', password: '', confirmPassword: '' })
const savingOperationPassword = ref(false)

async function fetchSettings() {
  try {
    const res = await getSettings()
    Object.assign(settings, res.data)
  } catch {}
}

async function fetchDisclaimers() {
  try { const res = await getDisclaimerTemplates(); disclaimerTemplates.value = res.data } catch {}
}

async function handleSave() {
  try { await updateSettings(settings); ElMessage.success('设置已保存') } catch {}
}

async function handleSaveCS() {
  try { await updateCustomerServiceConfig(csConfig); ElMessage.success('客服配置已保存') } catch {}
}

async function handleSaveDisclaimer(tpl: any) {
  try { await updateDisclaimerTemplate(tpl.id, { content: tpl.content }); ElMessage.success('免责声明已保存') } catch {}
}

async function handleSaveOperationPassword() {
  if (operationPasswordForm.oldPassword && !/^\d{6}$/.test(operationPasswordForm.oldPassword)) {
    ElMessage.warning('旧操作密码必须是6位数字')
    return
  }
  if (!/^\d{6}$/.test(operationPasswordForm.password)) {
    ElMessage.warning('操作密码必须是6位数字')
    return
  }
  if (operationPasswordForm.password !== operationPasswordForm.confirmPassword) {
    ElMessage.warning('两次输入的操作密码不一致')
    return
  }
  savingOperationPassword.value = true
  try {
    await updateOperationPassword({
      password: operationPasswordForm.password,
      ...(operationPasswordForm.oldPassword ? { old_password: operationPasswordForm.oldPassword } : {}),
    })
    operationPasswordForm.oldPassword = ''
    operationPasswordForm.password = ''
    operationPasswordForm.confirmPassword = ''
    ElMessage.success('操作密码已保存')
  } finally {
    savingOperationPassword.value = false
  }
}

onMounted(() => { fetchSettings(); fetchDisclaimers() })
</script>
