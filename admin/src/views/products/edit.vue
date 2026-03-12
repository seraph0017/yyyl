<template>
  <div class="page-container">
    <div class="card-box">
      <div class="flex-between mb-20">
        <h3>{{ isEdit ? '编辑商品' : '新增商品' }}</h3>
        <el-button @click="router.back()">返回</el-button>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-width="120px" style="max-width: 800px;">
        <el-form-item label="商品名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入商品名称" maxlength="50" show-word-limit />
        </el-form-item>

        <el-form-item label="商品品类" prop="category">
          <el-select v-model="form.category" placeholder="请选择品类" style="width: 100%;">
            <el-option v-for="(label, key) in categoryMap" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>

        <el-form-item label="基础价格（分）" prop="base_price">
          <el-input-number v-model="form.base_price" :min="0" :step="100" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="市场价（分）">
          <el-input-number v-model="form.market_price" :min="0" :step="100" style="width: 100%;" />
        </el-form-item>

        <el-form-item label="单位">
          <el-input v-model="form.unit" placeholder="如：晚、人次、份" />
        </el-form-item>

        <el-form-item label="封面图" prop="cover_image">
          <el-input v-model="form.cover_image" placeholder="请输入图片URL" />
        </el-form-item>

        <el-form-item label="商品描述">
          <el-input v-model="form.description" type="textarea" :rows="4" placeholder="请输入商品描述" />
        </el-form-item>

        <el-form-item label="排序权重">
          <el-input-number v-model="form.sort_order" :min="0" :max="9999" />
        </el-form-item>

        <el-form-item label="标签">
          <el-select v-model="form.tags" multiple filterable allow-create placeholder="添加标签" style="width: 100%;">
            <el-option label="热门" value="热门" />
            <el-option label="推荐" value="推荐" />
            <el-option label="新品" value="新品" />
            <el-option label="限时" value="限时" />
          </el-select>
        </el-form-item>

        <el-form-item label="需要身份登记">
          <el-switch v-model="form.require_identity" />
        </el-form-item>

        <el-form-item label="需要免责声明">
          <el-switch v-model="form.require_disclaimer" />
        </el-form-item>

        <el-form-item label="状态">
          <el-radio-group v-model="form.status">
            <el-radio value="draft">草稿</el-radio>
            <el-radio value="active">上架</el-radio>
            <el-radio value="inactive">下架</el-radio>
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
import { getProductDetail, createProduct, updateProduct } from '@/api/product'
import { categoryMap } from '@/utils'
import type { ProductCreateRequest } from '@/types'

const router = useRouter()
const route = useRoute()
const formRef = ref<FormInstance>()
const saving = ref(false)

const isEdit = computed(() => !!route.params.id)
const productId = computed(() => Number(route.params.id))

const form = reactive<ProductCreateRequest>({
  name: '',
  category: 'campsite',
  base_price: 0,
  market_price: undefined,
  unit: '',
  cover_image: '',
  images: [],
  description: '',
  sort_order: 0,
  tags: [],
  require_identity: false,
  require_disclaimer: false,
  status: 'draft',
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入商品名称', trigger: 'blur' }],
  category: [{ required: true, message: '请选择品类', trigger: 'change' }],
  base_price: [{ required: true, message: '请输入价格', trigger: 'blur' }],
  cover_image: [{ required: true, message: '请设置封面图', trigger: 'blur' }],
}

async function fetchDetail() {
  if (!isEdit.value) return
  try {
    const res = await getProductDetail(productId.value)
    Object.assign(form, res.data)
  } catch {}
}

async function handleSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()

  saving.value = true
  try {
    if (isEdit.value) {
      await updateProduct(productId.value, form)
      ElMessage.success('更新成功')
    } else {
      await createProduct(form)
      ElMessage.success('创建成功')
    }
    router.push('/products')
  } catch {} finally {
    saving.value = false
  }
}

onMounted(fetchDetail)
</script>
