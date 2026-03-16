<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>{{ isEdit ? '编辑营位' : '新增营位' }}</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="140px" style="max-width: 800px;">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="营位名称" prop="name">
          <el-input v-model="form.name" placeholder="如：A1 星空营位" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="营位类型" prop="type">
          <el-radio-group v-model="form.type">
            <el-radio value="daily_camping">日常营位</el-radio>
            <el-radio value="event_camping">活动营位</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="预定模式">
          <el-radio-group v-model="form.booking_mode">
            <el-radio value="by_position">按位置预定（孤品）</el-radio>
            <el-radio value="by_quantity">按人数预定（通品）</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="基础价格" prop="base_price">
          <el-input-number v-model="form.base_price" :min="0" :precision="2" :step="10" style="width: 200px;" />
          <span class="form-tip">元/晚</span>
        </el-form-item>

        <el-form-item label="封面图">
          <el-input v-model="coverUrl" placeholder="请输入图片URL" />
        </el-form-item>

        <el-form-item label="商品描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="营位描述，介绍环境、特色等" />
        </el-form-item>

        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>

        <!-- 营位属性 -->
        <el-divider content-position="left">营位属性</el-divider>

        <el-form-item label="所属区域">
          <el-input v-model="form.ext_camping.area" placeholder="如：A区、湖景区" style="width: 200px;" />
        </el-form-item>

        <el-form-item label="营位编号">
          <el-input v-model="form.ext_camping.position_name" placeholder="如：A01、B12" style="width: 200px;" />
        </el-form-item>

        <el-form-item label="最大人数">
          <el-input-number v-model="form.ext_camping.max_persons" :min="1" :max="20" />
          <span class="form-tip">人</span>
        </el-form-item>

        <el-form-item label="供电">
          <el-switch v-model="form.ext_camping.has_electricity" active-text="有电" inactive-text="无电" />
        </el-form-item>

        <el-form-item label="木平台">
          <el-switch v-model="form.ext_camping.has_platform" active-text="有" inactive-text="无" />
        </el-form-item>

        <el-form-item label="日照条件">
          <el-radio-group v-model="form.ext_camping.sun_exposure">
            <el-radio value="sunny">☀️ 全日照</el-radio>
            <el-radio value="shaded">🌳 树荫遮蔽</el-radio>
            <el-radio value="mixed">⛅ 半日照</el-radio>
          </el-radio-group>
        </el-form-item>

        <!-- 活动营位专有字段 -->
        <template v-if="form.type === 'event_camping'">
          <el-divider content-position="left">活动时间</el-divider>

          <el-form-item label="活动起始日">
            <el-date-picker v-model="form.ext_camping.event_start_date" type="date" placeholder="活动开始日期" value-format="YYYY-MM-DD" />
          </el-form-item>

          <el-form-item label="活动结束日">
            <el-date-picker v-model="form.ext_camping.event_end_date" type="date" placeholder="活动结束日期" value-format="YYYY-MM-DD" />
          </el-form-item>
        </template>

        <!-- 预订规则 -->
        <el-divider content-position="left">预订规则</el-divider>

        <el-form-item label="身份登记">
          <el-switch v-model="form.require_identity" active-text="需要" inactive-text="不需要" />
        </el-form-item>

        <el-form-item label="免责声明">
          <el-switch v-model="form.require_disclaimer" active-text="需签署" inactive-text="不需要" />
        </el-form-item>

        <el-form-item label="秒杀模式">
          <el-switch v-model="form.is_seckill" />
        </el-form-item>

        <el-form-item v-if="form.is_seckill" label="秒杀开始时间">
          <el-date-picker v-model="form.seckill_start_time" type="datetime" placeholder="秒杀开始时间" />
        </el-form-item>

        <el-form-item label="退票截止">
          <div class="refund-config">
            <span>使用日前</span>
            <el-input-number v-model="form.refund_deadline_value" :min="0" :max="365" style="width: 100px;" />
            <el-select v-model="form.refund_deadline_type" style="width: 100px;">
              <el-option label="天" value="days" />
              <el-option label="小时" value="hours" />
            </el-select>
            <span>可退票</span>
          </div>
        </el-form-item>

        <!-- 状态 -->
        <el-divider content-position="left">发布设置</el-divider>

        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="on_sale">上架</el-radio>
            <el-radio value="off_sale">下架</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="handleSubmit">保存</el-button>
          <el-button @click="router.back()">取消</el-button>
        </el-form-item>
      </el-form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { getCampsiteDetail, createCampsite, updateCampsite } from '@/api/campsite'
import type { CampsiteCreateRequest } from '@/types/campsite'

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const saving = ref(false)

const isEdit = computed(() => !!route.params.id)
const campsiteId = computed(() => Number(route.params.id))

const coverUrl = ref('')

const form = reactive<CampsiteCreateRequest & { ext_camping: any }>({
  name: '',
  type: 'daily_camping',
  description: '',
  base_price: 0,
  booking_mode: 'by_position',
  images: [],
  sort_order: 0,
  require_identity: true,
  require_disclaimer: true,
  is_seckill: false,
  seckill_start_time: undefined,
  normal_payment_timeout: 1800,
  seckill_payment_timeout: 600,
  refund_deadline_type: 'days',
  refund_deadline_value: 1,
  status: 'draft',
  ext_camping: {
    area: '',
    position_name: '',
    has_electricity: false,
    has_platform: false,
    sun_exposure: 'mixed',
    max_persons: 4,
    event_start_date: null,
    event_end_date: null,
  },
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入营位名称', trigger: 'blur' }],
  type: [{ required: true, message: '请选择营位类型', trigger: 'change' }],
  base_price: [{ required: true, message: '请输入基础价格', trigger: 'blur' }],
}

async function fetchDetail() {
  if (!isEdit.value) return
  try {
    const res = await getCampsiteDetail(campsiteId.value)
    const data = res.data
    // 映射到表单
    form.name = data.name
    form.type = data.type
    form.description = data.description
    form.base_price = parseFloat(data.base_price)
    form.booking_mode = data.booking_mode
    form.images = data.images || []
    form.sort_order = data.sort_order
    form.require_identity = data.require_identity
    form.require_disclaimer = data.require_disclaimer
    form.is_seckill = data.is_seckill
    form.seckill_start_time = data.seckill_start_time || undefined
    form.normal_payment_timeout = data.normal_payment_timeout
    form.seckill_payment_timeout = data.seckill_payment_timeout
    form.refund_deadline_type = data.refund_deadline_type
    form.refund_deadline_value = data.refund_deadline_value
    form.status = data.status

    if (data.ext_camping) {
      Object.assign(form.ext_camping, data.ext_camping)
    }

    // 封面图
    if (data.images?.length > 0) {
      coverUrl.value = data.images[0].url
    }
  } catch {}
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  saving.value = true
  try {
    // 组装images
    const submitData: any = { ...form }
    if (coverUrl.value) {
      submitData.images = [{ url: coverUrl.value, type: 'cover' }]
    }

    if (isEdit.value) {
      await updateCampsite(campsiteId.value, submitData)
      ElMessage.success('营位更新成功')
    } else {
      await createCampsite(submitData)
      ElMessage.success('营位创建成功')
    }
    router.push('/campsites')
  } catch {} finally {
    saving.value = false
  }
}

onMounted(fetchDetail)
</script>

<style lang="scss" scoped>
.form-tip {
  margin-left: 8px;
  color: var(--color-text-placeholder);
  font-size: 13px;
}

.refund-config {
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  font-size: 14px;
}
</style>
