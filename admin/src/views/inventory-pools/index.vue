<template>
  <div class="page-container">
    <div class="card-box">
      <el-tabs v-model="activeTab" class="inventory-tabs" @tab-change="handleTabChange">
        <el-tab-pane label="库存池列表" name="pools">
      <div class="flex-between mb-16">
        <div class="filter-bar">
          <el-input v-model.trim="keyword" placeholder="名称 / 编码" clearable style="width: 220px" @keyup.enter="handleSearch" />
          <el-select v-model="params.status" placeholder="状态" clearable style="width: 130px" @change="handleSearch">
            <el-option label="启用" value="active" />
            <el-option label="停用" value="inactive" />
          </el-select>
          <el-button type="primary" @click="handleSearch">
            <el-icon><Search /></el-icon>查询
          </el-button>
          <el-button @click="handleReset">重置</el-button>
        </div>
        <el-button type="primary" @click="openPoolDialog()">
          <el-icon><Plus /></el-icon>新增库存池
        </el-button>
      </div>

      <el-alert
        class="mb-16"
        type="warning"
        :closable="false"
        show-icon
        title="跨商品共享库存只允许通过本页显式绑定；不会按商品名称、分类或套餐关系自动共享。"
      />

      <el-table :data="pools" v-loading="loading" stripe>
        <el-table-column prop="pool_code" label="编码" min-width="150" show-overflow-tooltip />
        <el-table-column prop="name" label="名称" min-width="170" show-overflow-tooltip />
        <el-table-column label="类型" width="110" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ getPoolTypeLabel(row.pool_type) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="库存结构" min-width="260">
          <template #default="{ row }">
            <div class="stock-line">
              <span>总 {{ row.total }}</span>
              <span class="text-success">可用 {{ row.available }}</span>
              <span class="text-warning">锁定 {{ row.locked }}</span>
              <span class="text-info">已售 {{ row.sold }}</span>
            </div>
            <el-progress :percentage="getUsageRate(row)" :stroke-width="8" :show-text="false" />
          </template>
        </el-table-column>
        <el-table-column prop="binding_count" label="绑定数" width="90" align="center" />
        <el-table-column label="状态" width="90" align="center">
          <template #default="{ row }">
            <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
              {{ row.status === 'active' ? '启用' : '停用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="更新时间" width="170">
          <template #default="{ row }">{{ row.updated_at ? formatDateTime(row.updated_at) : '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right" align="center">
          <template #default="{ row }">
            <div class="action-buttons">
              <el-tooltip content="绑定管理" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--inventory" circle size="small" @click="openBindings(row)">
                  <el-icon><Connection /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip content="编辑" placement="top" :show-after="400">
                <el-button class="action-btn action-btn--edit" circle size="small" @click="openPoolDialog(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
              </el-tooltip>
              <el-tooltip :content="row.status === 'active' ? '停用' : '启用'" placement="top" :show-after="400">
                <el-button
                  class="action-btn"
                  :class="row.status === 'active' ? 'action-btn--offline' : 'action-btn--online'"
                  circle
                  size="small"
                  @click="togglePoolStatus(row)"
                >
                  <el-icon><TurnOff v-if="row.status === 'active'" /><Open v-else /></el-icon>
                </el-button>
              </el-tooltip>
            </div>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrapper">
        <el-pagination
          v-model:current-page="params.page"
          v-model:page-size="params.page_size"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next, jumper"
          @size-change="fetchPools"
          @current-change="fetchPools"
        />
      </div>
        </el-tab-pane>

        <el-tab-pane label="商品日历" name="calendar">
          <div class="calendar-toolbar">
            <div class="filter-bar">
              <el-date-picker
                v-model="calendarDateRange"
                type="daterange"
                range-separator="至"
                start-placeholder="开始日期"
                end-placeholder="结束日期"
                value-format="YYYY-MM-DD"
                :shortcuts="batchDateShortcuts"
              />
              <el-select v-model="calendarSource" style="width: 150px">
                <el-option label="全部来源" value="all" />
                <el-option label="普通库存" value="inventory" />
                <el-option label="共享库存" value="inventory_pool" />
              </el-select>
              <el-select
                v-model="calendarProductId"
                filterable
                remote
                clearable
                reserve-keyword
                :remote-method="searchProducts"
                :loading="productSearchLoading"
                placeholder="商品"
                style="width: 220px"
                @change="handleCalendarProductChange"
              >
                <el-option
                  v-for="item in productOptions"
                  :key="item.id"
                  :label="`${item.name} #${item.id}`"
                  :value="item.id"
                />
              </el-select>
              <el-select v-model="calendarSkuId" clearable placeholder="SKU" style="width: 190px" :disabled="!calendarProductId">
                <el-option
                  v-for="item in calendarSkuOptions"
                  :key="item.id"
                  :label="`${item.sku_name} #${item.id}`"
                  :value="item.id"
                />
              </el-select>
              <el-button type="primary" @click="fetchCalendar">
                <el-icon><Search /></el-icon>查询
              </el-button>
            </div>
            <el-button type="primary" @click="openBatchDrawer">
              <el-icon><Plus /></el-icon>批量调整
            </el-button>
          </div>

          <div class="calendar-legend">
            <span><i class="legend-dot legend-dot--inventory" />普通库存</span>
            <span><i class="legend-dot legend-dot--pool" />共享库存</span>
            <span><i class="legend-dot legend-dot--closed" />关闭</span>
          </div>

          <el-table :data="calendarRows" v-loading="calendarLoading" class="calendar-table" border>
            <el-table-column label="商品 / SKU" fixed min-width="230">
              <template #default="{ row }">
                <div class="calendar-row-title">{{ row.product_name }}</div>
                <div class="text-secondary">{{ formatCalendarRowSub(row) }}</div>
                <el-tag size="small" :type="row.inventory_source === 'inventory_pool' ? 'warning' : 'success'" effect="plain">
                  {{ row.inventory_source === 'inventory_pool' ? '共享库存' : '普通库存' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column
              v-for="day in calendarDates"
              :key="day"
              :label="formatCalendarColumn(day)"
              :label-class-name="isToday(day) ? 'calendar-column--today' : ''"
              :class-name="isToday(day) ? 'calendar-column--today' : ''"
              min-width="128"
              align="center"
            >
              <template #default="{ row }">
                <button
                  v-if="row.cells[day]"
                  class="calendar-cell"
                  :class="[
                    row.cells[day].inventory_source === 'inventory_pool' ? 'calendar-cell--pool' : 'calendar-cell--inventory',
                    row.cells[day].status === 'closed' ? 'calendar-cell--closed' : '',
                    isToday(day) ? 'calendar-cell--today' : '',
                  ]"
                  type="button"
                  @click="openCalendarCell(row.cells[day])"
                >
                  <strong>{{ row.cells[day].available }} / {{ row.cells[day].total }}</strong>
                  <span>锁 {{ row.cells[day].locked }} · 售 {{ row.cells[day].sold }}</span>
                  <em>{{ row.cells[day].status === 'open' ? '开启' : '关闭' }}</em>
                </button>
                <span v-else class="text-secondary">-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </div>

    <el-dialog v-model="poolDialogVisible" :title="editingPool ? '编辑库存池' : '新增库存池'" :width="poolDialogWidth" @closed="resetPoolForm">
      <el-form ref="poolFormRef" :model="poolForm" :rules="poolRules" label-width="112px">
        <el-form-item label="库存池编码" prop="pool_code">
          <el-input v-model.trim="poolForm.pool_code" :disabled="!!editingPool" placeholder="如 CAMP_SHARED_001" />
        </el-form-item>
        <el-form-item label="库存池名称" prop="name">
          <el-input v-model.trim="poolForm.name" placeholder="运营可识别名称" />
        </el-form-item>
        <el-form-item label="库存池类型" prop="pool_type">
          <el-select v-model="poolForm.pool_type" style="width: 100%">
            <el-option v-for="(label, value) in poolTypeMap" :key="value" :label="label" :value="value" />
          </el-select>
        </el-form-item>
        <el-form-item label="库存数量" required>
          <div class="stock-grid">
            <label class="stock-grid-item">
              <el-input-number v-model="poolForm.total" :min="0" controls-position="right" :disabled="!!editingPool" />
              <span>总库存</span>
            </label>
            <label class="stock-grid-item">
              <el-input-number v-model="poolForm.available" :min="0" controls-position="right" disabled />
              <span>可用</span>
            </label>
            <label class="stock-grid-item">
              <el-input-number v-model="poolForm.locked" :min="0" controls-position="right" disabled />
              <span>锁定</span>
            </label>
            <label class="stock-grid-item">
              <el-input-number v-model="poolForm.sold" :min="0" controls-position="right" disabled />
              <span>已售</span>
            </label>
          </div>
          <div class="form-tip" :class="{ 'form-tip--error': !isPoolQuantityValid }">
            当前校验：可用 + 锁定 + 已售 = {{ (poolForm.available || 0) + (poolForm.locked || 0) + (poolForm.sold || 0) }} / 总库存 {{ poolForm.total || 0 }}
          </div>
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="poolForm.status" disabled>
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="inactive">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="poolDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingPool" @click="savePool">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="bindingDrawerVisible" :size="bindingDrawerSize" :title="selectedPool ? `显式绑定 - ${selectedPool.name}` : '显式绑定'">
      <template v-if="selectedPool">
        <div class="binding-summary mb-16">
          <div><span>总库存</span><strong>{{ selectedPool.total }}</strong></div>
          <div><span>可用</span><strong class="text-success">{{ selectedPool.available }}</strong></div>
          <div><span>锁定</span><strong class="text-warning">{{ selectedPool.locked }}</strong></div>
          <div><span>已售</span><strong class="text-info">{{ selectedPool.sold }}</strong></div>
        </div>

        <div class="flex-between mb-16">
          <span class="drawer-note">只会共享下方显式绑定的商品或 SKU。</span>
          <el-button type="primary" @click="openBindingDialog()">
            <el-icon><Plus /></el-icon>新增绑定
          </el-button>
        </div>

        <el-table :data="bindings" v-loading="bindingLoading" stripe>
          <el-table-column label="绑定目标" min-width="210">
            <template #default="{ row }">
              <div>{{ getBindingTargetLabel(row.target_type) }} #{{ row.target_id || '-' }}</div>
              <div class="text-secondary">{{ row.target_name || '未返回目标名称' }}</div>
            </template>
          </el-table-column>
          <el-table-column prop="priority" label="优先级" width="90" align="center" />
          <el-table-column label="状态" width="90" align="center">
            <template #default="{ row }">
              <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                {{ row.status === 'active' ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" width="165">
            <template #default="{ row }">{{ row.updated_at ? formatDateTime(row.updated_at) : '-' }}</template>
          </el-table-column>
          <el-table-column label="操作" width="120" fixed="right" align="center">
            <template #default="{ row }">
              <div class="action-buttons">
                <el-tooltip content="编辑" placement="top" :show-after="400">
                  <el-button class="action-btn action-btn--edit" circle size="small" @click="openBindingDialog(row)">
                    <el-icon><Edit /></el-icon>
                  </el-button>
                </el-tooltip>
                <el-tooltip :content="row.status === 'active' ? '停用' : '启用'" placement="top" :show-after="400">
                  <el-button
                    class="action-btn"
                    :class="row.status === 'active' ? 'action-btn--offline' : 'action-btn--online'"
                    circle
                    size="small"
                    @click="toggleBindingStatus(row)"
                  >
                    <el-icon><TurnOff v-if="row.status === 'active'" /><Open v-else /></el-icon>
                  </el-button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </template>
    </el-drawer>

    <el-dialog v-model="bindingDialogVisible" :title="editingBinding ? '编辑绑定' : '新增绑定'" :width="bindingDialogWidth" @closed="resetBindingForm">
      <el-form ref="bindingFormRef" :model="bindingForm" :rules="bindingRules" label-width="112px">
        <el-form-item label="目标类型" prop="target_type">
          <el-radio-group v-model="bindingTargetType" :disabled="!!editingBinding" @change="clearTargetIds">
            <el-radio-button label="product">商品</el-radio-button>
            <el-radio-button label="sku">SKU</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="商品" required>
          <el-select
            v-model="selectedProductId"
            filterable
            remote
            reserve-keyword
            clearable
            :remote-method="searchProducts"
            :loading="productSearchLoading"
            placeholder="搜索商品名称后选择"
            style="width: 100%"
            @change="handleSelectedProductChange"
          >
            <el-option
              v-for="item in productOptions"
              :key="item.id"
              :label="`${item.name} #${item.id}`"
              :value="item.id"
            />
          </el-select>
          <div class="form-tip">共享库存只绑定明确选择的商品或 SKU。</div>
        </el-form-item>
        <el-form-item label="SKU" v-if="bindingTargetType === 'sku'" required>
          <el-select v-model="selectedSkuId" clearable placeholder="请选择商品下的 SKU" style="width: 100%">
            <el-option
              v-for="item in skuOptions"
              :key="item.id"
              :label="`${item.sku_name} #${item.id}`"
              :value="item.id"
            />
          </el-select>
          <div class="form-tip" v-if="selectedProduct && skuOptions.length === 0">该商品暂无可选 SKU，请改选商品绑定。</div>
        </el-form-item>
        <el-form-item label="优先级" prop="priority">
          <el-input-number v-model="bindingForm.priority" :min="1" :max="999" controls-position="right" />
        </el-form-item>
        <el-form-item label="状态" prop="status">
          <el-radio-group v-model="bindingForm.status">
            <el-radio-button label="active">启用</el-radio-button>
            <el-radio-button label="inactive">停用</el-radio-button>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="bindingDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingBinding" @click="saveBinding">保存</el-button>
      </template>
    </el-dialog>

    <el-drawer v-model="batchDrawerVisible" title="批量调整商品日历" :size="batchDrawerSize" @closed="resetBatchForm">
      <el-form ref="batchFormRef" :model="batchForm" :rules="batchRules" label-width="104px">
        <el-form-item label="调整目标">
          <el-select v-model="batchForm.row_keys" multiple collapse-tags collapse-tags-tooltip filterable placeholder="请选择商品 / SKU 行" style="width: 100%">
            <el-option
              v-for="row in calendarRows"
              :key="row.row_key"
              :label="formatBatchTargetLabel(row)"
              :value="row.row_key"
            />
          </el-select>
          <div class="form-tip">可多选当前商品日历中的商品或 SKU 行；共享库存行仅支持批量调价，库存请在共享库存池中调整。</div>
        </el-form-item>
        <el-form-item label="日期" prop="date_range">
          <el-radio-group v-model="batchDateMode" class="date-mode-toggle">
            <el-radio-button label="range">日期范围</el-radio-button>
            <el-radio-button label="dates">多选日期</el-radio-button>
          </el-radio-group>
          <el-date-picker
            v-if="batchDateMode === 'range'"
            v-model="batchDateRange"
            type="daterange"
            range-separator="至"
            start-placeholder="开始日期"
            end-placeholder="结束日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
            :shortcuts="batchDateShortcuts"
          />
          <el-date-picker
            v-else
            v-model="batchSelectedDates"
            type="dates"
            placeholder="请选择一个或多个日期"
            value-format="YYYY-MM-DD"
            style="width: 100%"
          />
        </el-form-item>
        <el-form-item v-if="batchDateMode === 'range'" label="星期">
          <el-checkbox-group v-model="batchForm.weekdays">
            <el-checkbox-button v-for="item in weekdayOptions" :key="item.value" :label="item.value">{{ item.label }}</el-checkbox-button>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="调整内容">
          <el-radio-group v-model="batchForm.content">
            <el-radio-button label="inventory">库存</el-radio-button>
            <el-radio-button label="price">价格</el-radio-button>
            <el-radio-button label="both">库存+价格</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <template v-if="batchForm.content !== 'price'">
          <el-form-item label="库存模式" prop="mode">
            <el-radio-group v-model="batchForm.mode">
              <el-radio-button label="set_total">设总量</el-radio-button>
              <el-radio-button label="adjust_total">增减</el-radio-button>
              <el-radio-button label="open">开启</el-radio-button>
              <el-radio-button label="close">关闭</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.mode === 'set_total'" label="总库存">
            <el-input-number v-model="batchForm.total" :min="0" controls-position="right" />
          </el-form-item>
          <el-form-item v-if="batchForm.mode === 'adjust_total'" label="调整量">
            <el-input-number v-model="batchForm.delta" controls-position="right" />
          </el-form-item>
          <el-form-item v-if="batchForm.mode === 'set_total'" label="状态">
            <el-radio-group v-model="batchForm.status">
              <el-radio-button label="open">开启</el-radio-button>
              <el-radio-button label="closed">关闭</el-radio-button>
            </el-radio-group>
          </el-form-item>
        </template>
        <template v-if="batchForm.content !== 'inventory'">
          <el-form-item label="价格模式">
            <el-radio-group v-model="batchForm.price_mode">
              <el-radio-button label="set_total">总价</el-radio-button>
              <el-radio-button label="adjust_total">增减</el-radio-button>
            </el-radio-group>
          </el-form-item>
          <el-form-item v-if="batchForm.price_mode === 'set_total'" label="目标总价">
            <el-input-number v-model="batchForm.price_total" :min="0" :precision="2" controls-position="right" />
          </el-form-item>
          <el-form-item v-if="batchForm.price_mode === 'adjust_total'" label="价格增减">
            <el-input-number v-model="batchForm.price_delta" :precision="2" controls-position="right" />
          </el-form-item>
        </template>
        <el-form-item label="备注">
          <el-input v-model.trim="batchForm.remark" type="textarea" :rows="3" maxlength="120" show-word-limit />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="batchDrawerVisible = false">取消</el-button>
        <el-button type="primary" :loading="savingBatch" @click="saveBatchInventory">保存</el-button>
      </template>
    </el-drawer>

    <el-drawer v-model="calendarCellDrawerVisible" title="库存格详情" :size="calendarCellDrawerSize">
      <template v-if="selectedCalendarCell">
        <div class="cell-detail">
          <div><span>商品</span><strong>{{ selectedCalendarCell.product_name }}</strong></div>
          <div><span>SKU</span><strong>{{ selectedCalendarCell.sku_name || selectedCalendarCell.sku_code || '-' }}</strong></div>
          <div><span>日期</span><strong>{{ selectedCalendarCell.date }}</strong></div>
          <div><span>库存</span><strong>{{ selectedCalendarCell.available }} / {{ selectedCalendarCell.total }}</strong></div>
          <div><span>锁定</span><strong>{{ selectedCalendarCell.locked }}</strong></div>
          <div><span>已售</span><strong>{{ selectedCalendarCell.sold }}</strong></div>
        </div>

        <template v-if="selectedCalendarCell.inventory_source === 'inventory_pool'">
          <el-divider />
          <el-form label-width="96px">
            <el-form-item label="共享库存池">
              <el-tag type="warning" effect="plain">{{ selectedCalendarPool.name || selectedCalendarPool.pool_code }}</el-tag>
            </el-form-item>
            <el-form-item label="调整模式">
              <el-radio-group v-model="poolAdjustForm.mode">
                <el-radio-button label="set_total">设总量</el-radio-button>
                <el-radio-button label="adjust_total">增减</el-radio-button>
                <el-radio-button label="set_status">状态</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item v-if="poolAdjustForm.mode === 'set_total'" label="总库存">
              <el-input-number v-model="poolAdjustForm.total" :min="0" controls-position="right" />
            </el-form-item>
            <el-form-item v-if="poolAdjustForm.mode === 'adjust_total'" label="调整量">
              <el-input-number v-model="poolAdjustForm.delta" controls-position="right" />
            </el-form-item>
            <el-form-item label="状态">
              <el-radio-group v-model="poolAdjustForm.status">
                <el-radio-button label="active">启用</el-radio-button>
                <el-radio-button label="inactive">停用</el-radio-button>
              </el-radio-group>
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model.trim="poolAdjustForm.remark" maxlength="120" />
            </el-form-item>
          </el-form>
          <div class="drawer-actions">
            <el-button type="primary" :loading="savingPoolAdjust" @click="savePoolAdjust">保存共享池调整</el-button>
          </div>
        </template>
      </template>
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox, type FormInstance, type FormRules } from 'element-plus'
import { Connection, Edit, Open, Plus, Search, TurnOff } from '@element-plus/icons-vue'
import {
  adjustInventoryPool,
  batchUpdateInventoryCalendar,
  createInventoryPool,
  createInventoryPoolBinding,
  getInventoryCalendar,
  getInventoryPoolBindings,
  getInventoryPools,
  updateInventoryPool,
  updateInventoryPoolBinding,
} from '@/api/inventory-pool'
import { getProductDetail, getProducts } from '@/api/product'
import { formatDateTime } from '@/utils'
import type { Product, ProductSKU } from '@/types'
import type {
  InventoryPool,
  InventoryBatchContent,
  InventoryBatchPayload,
  InventoryCalendarCell,
  InventoryCalendarRow,
  InventoryCalendarSourceFilter,
  InventoryPoolAdjustPayload,
  InventoryPoolBinding,
  InventoryPoolBindingPayload,
  InventoryPoolBindingTargetType,
  InventoryPoolPayload,
  InventoryPoolType,
} from '@/types/inventory-pool'

const poolTypeMap: Record<InventoryPoolType, string> = {
  generic: '通用',
  campsite: '营位',
  activity: '活动',
  rental: '租赁',
  bundle: '组合',
}

const bindingTargetMap: Record<InventoryPoolBindingTargetType, string> = {
  product: '商品',
  sku: 'SKU',
  unsupported: '不支持目标',
}

const loading = ref(false)
const activeTab = ref('pools')
const pools = ref<InventoryPool[]>([])
const total = ref(0)
const keyword = ref('')
const params = reactive({ page: 1, page_size: 20, status: undefined as InventoryPool['status'] | undefined })
const poolDialogWidth = 'min(560px, calc(100vw - 32px))'
const bindingDialogWidth = 'min(520px, calc(100vw - 32px))'
const bindingDrawerSize = 'min(720px, 92vw)'
const batchDrawerSize = 'min(520px, 92vw)'
const calendarCellDrawerSize = 'min(460px, 92vw)'

const poolDialogVisible = ref(false)
const savingPool = ref(false)
const editingPool = ref<InventoryPool | null>(null)
const poolFormRef = ref<FormInstance>()
const poolForm = reactive<InventoryPoolPayload>({
  pool_code: '',
  name: '',
  pool_type: 'generic',
  total: 0,
  available: 0,
  locked: 0,
  sold: 0,
  status: 'active',
})

const bindingDrawerVisible = ref(false)
const selectedPool = ref<InventoryPool | null>(null)
const bindingLoading = ref(false)
const bindings = ref<InventoryPoolBinding[]>([])
const bindingDialogVisible = ref(false)
const savingBinding = ref(false)
const editingBinding = ref<InventoryPoolBinding | null>(null)
const bindingFormRef = ref<FormInstance>()
type EditableBindingTargetType = 'product' | 'sku'
const bindingTargetType = ref<EditableBindingTargetType>('product')
const bindingForm = reactive<InventoryPoolBindingPayload>({
  product_id: null,
  sku_id: null,
  priority: 100,
  status: 'active',
})
const productSearchLoading = ref(false)
const productOptions = ref<Product[]>([])
const selectedProductId = ref<number | undefined>()
const selectedSkuId = ref<number | undefined>()
const selectedProduct = computed(() => productOptions.value.find(item => item.id === selectedProductId.value))
const skuOptions = computed<ProductSKU[]>(() => selectedProduct.value?.skus || [])

const today = new Date()
const calendarDateRange = ref<[string, string]>([formatDate(today), formatDate(addDays(today, 13))])
const calendarSource = ref<InventoryCalendarSourceFilter>('all')
const calendarProductId = ref<number | undefined>()
const calendarSkuId = ref<number | undefined>()
const calendarLoading = ref(false)
const calendarRawRows = ref<InventoryCalendarRow[]>([])
const calendarCells = ref<InventoryCalendarCell[]>([])
const calendarProduct = computed(() => productOptions.value.find(item => item.id === calendarProductId.value))
const calendarSkuOptions = computed<ProductSKU[]>(() => calendarProduct.value?.skus || [])

const batchDrawerVisible = ref(false)
const savingBatch = ref(false)
const batchFormRef = ref<FormInstance>()
const batchDateMode = ref<'range' | 'dates'>('range')
const batchDateRange = ref<[string, string]>([formatDate(today), formatDate(addDays(today, 13))])
const batchSelectedDates = ref<string[]>([])
const batchForm = reactive({
  row_keys: [] as string[],
  content: 'inventory' as InventoryBatchContent,
  mode: 'set_total' as 'set_total' | 'adjust_total' | 'open' | 'close',
  total: 0,
  delta: 0,
  status: 'open' as 'open' | 'closed',
  price_mode: 'set_total' as 'set_total' | 'adjust_total',
  price_total: 0,
  price_delta: 0,
  weekdays: [] as number[],
  remark: '',
})

const calendarCellDrawerVisible = ref(false)
const selectedCalendarCell = ref<InventoryCalendarCell | null>(null)
const selectedCalendarPool = reactive({
  id: 0,
  pool_code: '',
  name: '',
})
const savingPoolAdjust = ref(false)
const poolAdjustForm = reactive<InventoryPoolAdjustPayload>({
  mode: 'set_total',
  total: 0,
  delta: 0,
  status: 'active',
  remark: '',
})

const weekdayOptions = [
  { label: '一', value: 0 },
  { label: '二', value: 1 },
  { label: '三', value: 2 },
  { label: '四', value: 3 },
  { label: '五', value: 4 },
  { label: '六', value: 5 },
  { label: '日', value: 6 },
]

interface CalendarTableRow extends InventoryCalendarRow {
  row_key: string
  cells: Record<string, InventoryCalendarCell>
}

const calendarDates = computed(() => {
  return Array.from(new Set(calendarCells.value.map(item => item.date))).sort()
})

const calendarRows = computed<CalendarTableRow[]>(() => {
  const rows = new Map<string, CalendarTableRow>()
  calendarRawRows.value.forEach(row => {
    const rowKey = `${row.product_id}:${row.sku_id || 0}:${row.time_slot || ''}:${row.inventory_source}`
    rows.set(rowKey, { ...row, row_key: rowKey, cells: {} })
  })
  calendarCells.value.forEach(cell => {
    const rowKey = `${cell.product_id}:${cell.sku_id || 0}:${cell.time_slot || ''}:${cell.inventory_source}`
    if (!rows.has(rowKey)) {
      rows.set(rowKey, {
        row_key: rowKey,
        product_id: cell.product_id,
        product_name: cell.product_name,
        sku_id: cell.sku_id,
        sku_code: cell.sku_code,
        sku_name: cell.sku_name,
        time_slot: cell.time_slot || null,
        inventory_source: cell.inventory_source,
        inventory_pool_id: cell.inventory_pool_id,
        inventory_pool_code: cell.inventory_pool_code,
        inventory_pool_name: cell.inventory_pool_name,
        cells: {},
      })
    }
    rows.get(rowKey)!.cells[cell.date] = cell
  })
  return Array.from(rows.values())
})

const isPoolQuantityValid = computed(() => {
  return (poolForm.available || 0) + (poolForm.locked || 0) + (poolForm.sold || 0) === (poolForm.total || 0)
})

watch(
  () => poolForm.total,
  (total) => {
    if (editingPool.value) return
    poolForm.available = total || 0
    poolForm.locked = 0
    poolForm.sold = 0
    poolForm.status = 'active'
  },
)

const poolRules: FormRules = {
  pool_code: [{ required: true, message: '请输入库存池编码', trigger: 'blur' }],
  name: [{ required: true, message: '请输入库存池名称', trigger: 'blur' }],
  pool_type: [{ required: true, message: '请选择库存池类型', trigger: 'change' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const bindingRules: FormRules = {
  priority: [{ required: true, message: '请输入优先级', trigger: 'blur' }],
  status: [{ required: true, message: '请选择状态', trigger: 'change' }],
}

const batchRules: FormRules = {
  mode: [{ required: true, message: '请选择调整模式', trigger: 'change' }],
}

function addDays(value: Date, days: number) {
  const next = new Date(value)
  next.setDate(next.getDate() + days)
  return next
}

function formatDate(value: Date) {
  const year = value.getFullYear()
  const month = `${value.getMonth() + 1}`.padStart(2, '0')
  const day = `${value.getDate()}`.padStart(2, '0')
  return `${year}-${month}-${day}`
}

const batchDateShortcuts = [
  { text: '最近一个月', value: () => buildRecentRange(1, 'month') },
  { text: '最近三个月', value: () => buildRecentRange(3, 'month') },
  { text: '最近半年', value: () => buildRecentRange(6, 'month') },
  { text: '最近一年', value: () => buildRecentRange(1, 'year') },
]

function isToday(value: string): boolean {
  return value === formatDate(new Date())
}

function buildRecentRange(amount: number, unit: 'month' | 'year'): [Date, Date] {
  const start = new Date()
  start.setHours(0, 0, 0, 0)
  const end = new Date(start)
  if (unit === 'month') {
    end.setMonth(end.getMonth() + amount)
  } else {
    end.setFullYear(end.getFullYear() + amount)
  }
  end.setDate(end.getDate() - 1)
  return [start, end]
}

function formatCalendarColumn(value: string) {
  const day = new Date(`${value}T00:00:00`)
  const label = `${day.getMonth() + 1}/${day.getDate()}`
  return isToday(value) ? `今天 ${label}` : label
}

function formatCalendarRowSub(row: CalendarTableRow): string {
  const parts = [row.sku_name || row.sku_code, row.time_slot ? `场次 ${row.time_slot}` : ''].filter(Boolean)
  return parts.join(' · ') || '商品库存'
}

function formatBatchTargetLabel(row: CalendarTableRow): string {
  const suffix = formatCalendarRowSub(row)
  const source = row.inventory_source === 'inventory_pool' ? '共享库存' : '普通库存'
  return `${row.product_name} #${row.product_id}${suffix ? ` · ${suffix}` : ''} · ${source}`
}

function handleTabChange(name: string | number) {
  if (name === 'calendar' && calendarCells.value.length === 0) {
    fetchCalendar()
  }
}

function getUsageRate(row: InventoryPool) {
  if (!row.total) return 0
  return Math.round(((row.locked + row.sold) / row.total) * 100)
}

function getPoolTypeLabel(type: string) {
  return poolTypeMap[type as InventoryPoolType] || type
}

function getBindingTargetLabel(type: string) {
  return bindingTargetMap[type as InventoryPoolBindingTargetType] || type
}

async function fetchPools() {
  loading.value = true
  try {
    const res = await getInventoryPools({
      page: params.page,
      page_size: params.page_size,
      keyword: keyword.value.trim() || undefined,
      status: params.status,
    })
    pools.value = res.data.items
    total.value = res.data.total
  } finally {
    loading.value = false
  }
}

async function fetchCalendar() {
  if (!calendarDateRange.value?.[0] || !calendarDateRange.value?.[1]) {
    ElMessage.error('请选择商品日历日期范围')
    return
  }
  calendarLoading.value = true
  try {
    const res = await getInventoryCalendar({
      date_start: calendarDateRange.value[0],
      date_end: calendarDateRange.value[1],
      product_ids: calendarProductId.value ? [calendarProductId.value] : undefined,
      sku_ids: calendarSkuId.value ? [calendarSkuId.value] : undefined,
      inventory_source: calendarSource.value,
      include_missing: true,
    })
    calendarRawRows.value = res.data.rows
    calendarCells.value = res.data.cells
  } finally {
    calendarLoading.value = false
  }
}

function handleSearch() {
  params.page = 1
  fetchPools()
}

function handleReset() {
  keyword.value = ''
  params.status = undefined
  handleSearch()
}

function resetPoolForm() {
  editingPool.value = null
  Object.assign(poolForm, {
    pool_code: '',
    name: '',
    pool_type: 'generic',
    total: 0,
    available: 0,
    locked: 0,
    sold: 0,
    status: 'active',
  })
  poolFormRef.value?.clearValidate()
}

function openPoolDialog(row?: InventoryPool) {
  if (row) {
    editingPool.value = row
    Object.assign(poolForm, {
      pool_code: row.pool_code,
      name: row.name,
      pool_type: row.pool_type,
      total: row.total,
      available: row.available,
      locked: row.locked,
      sold: row.sold,
      status: row.status,
    })
  }
  poolDialogVisible.value = true
}

async function savePool() {
  const valid = await poolFormRef.value?.validate().catch(() => false)
  if (!valid) return
  if (!isPoolQuantityValid.value) {
    ElMessage.error('可用、锁定、已售之和必须等于总库存')
    return
  }
  const quantityChange = editingPool.value
    ? `确认更新共享库存池「${poolForm.name}」的名称和类型。`
    : `即将创建共享库存池「${poolForm.name}」，总量 ${poolForm.total}；共享库存不会自动绑定商品/SKU，需在绑定抽屉中显式绑定。`
  const action = editingPool.value
    ? `inventory_pool:update:${editingPool.value.id}`
    : 'inventory_pool:create'
  const payload: Partial<InventoryPoolPayload> = editingPool.value
    ? { name: poolForm.name, pool_type: poolForm.pool_type }
    : {
      pool_code: poolForm.pool_code,
      name: poolForm.name,
      pool_type: poolForm.pool_type,
      total: poolForm.total || 0,
      available: poolForm.total || 0,
      locked: 0,
      sold: 0,
      status: 'active' as const,
    }
  try {
    await ElMessageBox.confirm(quantityChange, '共享库存保存确认', { type: 'warning' })
  } catch {
    return
  }
  savingPool.value = true
  try {
    if (editingPool.value) {
      await updateInventoryPool(editingPool.value.id, payload)
    } else {
      await createInventoryPool(payload as InventoryPoolPayload)
    }
    ElMessage.success('库存池已保存')
    poolDialogVisible.value = false
    fetchPools()
  } finally {
    savingPool.value = false
  }
}

async function togglePoolStatus(row: InventoryPool) {
  const status = row.status === 'active' ? 'inactive' : 'active'
  try {
    await ElMessageBox.confirm(
      `确认${status === 'active' ? '启用' : '停用'}库存池「${row.name}」？该操作会影响所有显式绑定商品/SKU。`,
      '确认库存池状态变更',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  const payload: InventoryPoolAdjustPayload = { mode: 'set_status', status }
  await adjustInventoryPool(row.id, payload)
  ElMessage.success(status === 'active' ? '库存池已启用' : '库存池已停用')
  fetchPools()
}

async function openBindings(row: InventoryPool) {
  selectedPool.value = row
  bindingDrawerVisible.value = true
  await fetchBindings()
}

async function fetchBindings() {
  if (!selectedPool.value) return
  bindingLoading.value = true
  try {
    const res = await getInventoryPoolBindings(selectedPool.value.id)
    bindings.value = res.data
  } finally {
    bindingLoading.value = false
  }
}

function clearTargetIds() {
  selectedProductId.value = undefined
  selectedSkuId.value = undefined
  Object.assign(bindingForm, {
    product_id: null,
    sku_id: null,
  })
}

function resetBindingForm() {
  editingBinding.value = null
  bindingTargetType.value = 'product'
  selectedProductId.value = undefined
  selectedSkuId.value = undefined
  Object.assign(bindingForm, {
    product_id: null,
    sku_id: null,
    priority: 100,
    status: 'active',
  })
  bindingFormRef.value?.clearValidate()
}

function openBindingDialog(row?: InventoryPoolBinding) {
  if (row) {
    editingBinding.value = row
    bindingTargetType.value = row.target_type === 'sku' ? 'sku' : 'product'
    const productId = deriveBindingProductId(row)
    selectedProductId.value = productId
    selectedSkuId.value = row.sku_id || undefined
    Object.assign(bindingForm, {
      product_id: productId || null,
      sku_id: row.sku_id,
      priority: row.priority,
      status: row.status,
    })
    ensureBindingProductOption(row, productId)
  }
  bindingDialogVisible.value = true
}

async function searchProducts(keyword: string) {
  productSearchLoading.value = true
  try {
    const res = await getProducts({
      page: 1,
      page_size: 20,
      keyword: keyword.trim() || undefined,
    })
    productOptions.value = res.data.list
  } finally {
    productSearchLoading.value = false
  }
}

function deriveBindingProductId(row: InventoryPoolBinding): number | undefined {
  if (row.product_id) return row.product_id
  if (!row.sku_id) return undefined
  return productOptions.value.find(product => product.skus?.some(sku => sku.id === row.sku_id))?.id
}

function ensureBindingProductOption(row: InventoryPoolBinding, productId = deriveBindingProductId(row)) {
  if (!productId || productOptions.value.some(item => item.id === productId)) return
  productOptions.value.push({
    id: productId,
    name: row.target_name || `商品 #${productId}`,
    type: 'shop',
    category: 'shop_item',
    sub_category: '',
    status: 'on_sale',
    cover_image: '',
    images: [],
    description: '',
    base_price: 0,
    market_price: null,
    unit: '',
    sort_order: 0,
    tags: [],
    require_identity: false,
    require_disclaimer: false,
    created_at: '',
    updated_at: '',
    skus: row.sku_id ? [{
      id: row.sku_id,
      product_id: productId,
      sku_name: row.target_name || `SKU #${row.sku_id}`,
      sku_code: '',
      price: 0,
      stock: 0,
      attributes: {},
      status: 'active',
    }] : [],
  })
}

async function handleSelectedProductChange() {
  selectedSkuId.value = undefined
  if (selectedProductId.value) {
    await loadSelectedProductDetail(selectedProductId.value)
  }
}

async function handleCalendarProductChange() {
  calendarSkuId.value = undefined
  if (calendarProductId.value) {
    await loadSelectedProductDetail(calendarProductId.value)
  }
}

async function loadSelectedProductDetail(productId: number) {
  const current = productOptions.value.find(item => item.id === productId)
  if (current?.skus && current.skus.length > 0) return
  const res = await getProductDetail(productId)
  const detail = res.data
  const index = productOptions.value.findIndex(item => item.id === productId)
  if (index >= 0) {
    productOptions.value.splice(index, 1, { ...productOptions.value[index], ...detail })
  } else {
    productOptions.value.push(detail)
  }
}

function buildBindingPayload(): InventoryPoolBindingPayload | null {
  if (!selectedProductId.value) {
    ElMessage.error('请选择要绑定的商品')
    return null
  }
  if (bindingTargetType.value === 'sku' && !selectedSkuId.value) {
    ElMessage.error('请选择要绑定的 SKU')
    return null
  }
  const payload: InventoryPoolBindingPayload = {
    product_id: null,
    sku_id: null,
    priority: bindingForm.priority,
    status: bindingForm.status,
  }
  if (bindingTargetType.value === 'product') payload.product_id = selectedProductId.value
  if (bindingTargetType.value === 'sku') payload.sku_id = selectedSkuId.value
  return payload
}

async function saveBinding() {
  const valid = await bindingFormRef.value?.validate().catch(() => false)
  if (!valid || !selectedPool.value) return
  const payload = buildBindingPayload()
  if (!payload) return
  if (selectedProductId.value) {
    await loadSelectedProductDetail(selectedProductId.value)
  }
  const targetLabel = bindingTargetType.value === 'sku'
    ? `${selectedProduct.value?.name || '商品'} / ${skuOptions.value.find(item => item.id === selectedSkuId.value)?.sku_name || `SKU #${selectedSkuId.value}`}`
    : `${selectedProduct.value?.name || `商品 #${selectedProductId.value}`}`
  try {
    await ElMessageBox.confirm(
      `确认将库存池「${selectedPool.value.name}」显式绑定到「${targetLabel}」？保存后该目标会共用库存池库存。`,
      '确认共享库存绑定',
      { type: 'warning', confirmButtonText: '确认绑定', cancelButtonText: '取消' },
    )
  } catch {
    return
  }

  savingBinding.value = true
  try {
    if (editingBinding.value) {
      await updateInventoryPoolBinding(editingBinding.value.id, payload)
    } else {
      await createInventoryPoolBinding(selectedPool.value.id, payload)
    }
    ElMessage.success('绑定关系已保存')
    bindingDialogVisible.value = false
    fetchBindings()
    fetchPools()
  } finally {
    savingBinding.value = false
  }
}

async function toggleBindingStatus(row: InventoryPoolBinding) {
  const status = row.status === 'active' ? 'inactive' : 'active'
  try {
    await ElMessageBox.confirm(
      `确认${status === 'active' ? '启用' : '停用'}绑定「${getBindingTargetLabel(row.target_type)} #${row.target_id || '-'}」？`,
      '确认绑定状态变更',
      { type: 'warning', confirmButtonText: '确认', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  await updateInventoryPoolBinding(row.id, { status })
  ElMessage.success(status === 'active' ? '绑定已启用' : '绑定已停用')
  fetchBindings()
  fetchPools()
}

function openBatchDrawer() {
  batchDrawerVisible.value = true
  batchDateMode.value = 'range'
  batchDateRange.value = [...calendarDateRange.value]
  batchSelectedDates.value = []
  batchForm.row_keys = calendarRows.value
    .filter(row => {
      if (calendarProductId.value && row.product_id !== calendarProductId.value) return false
      if (calendarSkuId.value && row.sku_id !== calendarSkuId.value) return false
      return true
    })
    .map(row => row.row_key)
}

function resetBatchForm() {
  batchDateMode.value = 'range'
  batchDateRange.value = [...calendarDateRange.value]
  batchSelectedDates.value = []
  Object.assign(batchForm, {
    row_keys: [],
    content: 'inventory',
    mode: 'set_total',
    total: 0,
    delta: 0,
    status: 'open',
    price_mode: 'set_total',
    price_total: 0,
    price_delta: 0,
    weekdays: [],
    remark: '',
  })
  batchFormRef.value?.clearValidate()
}

function buildBatchPayload(): InventoryBatchPayload | null {
  const selectedTargets = calendarRows.value.filter(row => batchForm.row_keys.includes(row.row_key))
  if (!selectedTargets.length) {
    ElMessage.error('请选择要调整的商品 / SKU 行')
    return null
  }
  if (batchDateMode.value === 'range' && (!batchDateRange.value?.[0] || !batchDateRange.value?.[1])) {
    ElMessage.error('请选择日期范围')
    return null
  }
  if (batchDateMode.value === 'dates' && batchSelectedDates.value.length === 0) {
    ElMessage.error('请选择需要调整的日期')
    return null
  }
  const hasSharedTargets = selectedTargets.some(row => row.inventory_source === 'inventory_pool')
  if (batchForm.content !== 'price' && hasSharedTargets) {
    ElMessage.error('共享库存行请在库存池中调整库存；如需批量改价请选择“价格”')
    return null
  }
  const skuIds = Array.from(new Set(selectedTargets.map(row => row.sku_id).filter((id): id is number => !!id)))
  const hasSkuTargets = skuIds.length > 0
  const hasProductLevelTargets = selectedTargets.some(row => !row.sku_id)
  if (hasSkuTargets && hasProductLevelTargets) {
    ElMessage.error('商品级行和 SKU 行不能混选，请分开批量调整')
    return null
  }
  if (batchForm.content !== 'inventory' && hasSkuTargets) {
    ElMessage.error('SKU 价格优先，批量调价请选择商品级行')
    return null
  }
  const timeSlots = Array.from(new Set(selectedTargets.map(row => row.time_slot || '').filter(Boolean)))
  if (timeSlots.length > 1) {
    ElMessage.error('多选批量调整暂不支持混合多个活动场次')
    return null
  }
  const batchPayload: InventoryBatchPayload = {
    product_ids: Array.from(new Set(selectedTargets.map(row => row.product_id))),
    mode: batchForm.content === 'price' ? 'open' : batchForm.mode,
    adjust_inventory: batchForm.content !== 'price',
    create_missing: true,
  }
  if (batchDateMode.value === 'dates') {
    batchPayload.dates = [...batchSelectedDates.value]
  } else {
    batchPayload.date_start = batchDateRange.value[0]
    batchPayload.date_end = batchDateRange.value[1]
  }
  if (batchDateMode.value === 'range' && batchForm.weekdays?.length) {
    batchPayload.weekdays = [...batchForm.weekdays]
  }
  if (hasSkuTargets) {
    batchPayload.sku_ids = skuIds
  }
  if (timeSlots[0]) {
    batchPayload.time_slot = timeSlots[0]
  }
  const remark = batchForm.remark?.trim()
  if (remark) {
    batchPayload.remark = remark
  }
  if (batchForm.content !== 'price') {
    if (batchForm.mode === 'adjust_total') {
      batchPayload.delta = batchForm.delta || 0
    } else if (batchForm.mode === 'set_total') {
      batchPayload.total = batchForm.total || 0
      batchPayload.status = batchForm.status
    } else if (batchForm.mode === 'open') {
      batchPayload.status = 'open'
    } else if (batchForm.mode === 'close') {
      batchPayload.status = 'closed'
    }
  }
  if (batchForm.content !== 'inventory') {
    batchPayload.price_mode = batchForm.price_mode
    if (batchForm.price_mode === 'set_total') {
      batchPayload.price_total = batchForm.price_total || 0
    } else {
      batchPayload.price_delta = batchForm.price_delta || 0
    }
  }
  return batchPayload
}

function getBatchDateSummary(): string {
  if (batchDateMode.value === 'dates') {
    const sortedDates = [...batchSelectedDates.value].sort()
    if (sortedDates.length <= 3) return sortedDates.join('、')
    return `${sortedDates.slice(0, 3).join('、')} 等 ${sortedDates.length} 天`
  }
  return `${batchDateRange.value[0]} 至 ${batchDateRange.value[1]}`
}

async function saveBatchInventory() {
  const valid = await batchFormRef.value?.validate().catch(() => false)
  if (!valid) return
  const batchPayload = buildBatchPayload()
  if (!batchPayload) return
  const batchFormPayload = { ...batchPayload }
  try {
    await ElMessageBox.confirm(`确认批量调整 ${getBatchDateSummary()} 的商品日历？`, '商品日历批量调整确认', { type: 'warning' })
  } catch {
    return
  }
  savingBatch.value = true
  try {
    const res = await batchUpdateInventoryCalendar(batchFormPayload)
    const priceText = res.data.price_created_count || res.data.price_updated_count
      ? `，价格新增 ${res.data.price_created_count || 0} 条、更新 ${res.data.price_updated_count || 0} 条`
      : ''
    ElMessage.success(`库存创建 ${res.data.created_count} 条、更新 ${res.data.updated_count} 条${priceText}`)
    batchDrawerVisible.value = false
    fetchCalendar()
    fetchPools()
  } finally {
    savingBatch.value = false
  }
}

function openCalendarCell(cell: InventoryCalendarCell) {
  selectedCalendarCell.value = cell
  Object.assign(selectedCalendarPool, {
    id: cell.inventory_pool_id || 0,
    pool_code: cell.inventory_pool_code || '',
    name: cell.inventory_pool_name || '',
  })
  Object.assign(poolAdjustForm, {
    mode: 'set_total',
    total: cell.total,
    delta: 0,
    status: cell.status === 'open' ? 'active' : 'inactive',
    remark: '',
  })
  calendarCellDrawerVisible.value = true
}

async function savePoolAdjust() {
  if (!selectedCalendarPool.id || !selectedCalendarCell.value) return
  const payload: InventoryPoolAdjustPayload = {
    mode: poolAdjustForm.mode,
    status: poolAdjustForm.status,
  }
  const remark = poolAdjustForm.remark?.trim()
  if (remark) {
    payload.remark = remark
  }
  if (poolAdjustForm.mode === 'set_total') {
    payload.total = poolAdjustForm.total || 0
  }
  if (poolAdjustForm.mode === 'adjust_total') {
    payload.delta = poolAdjustForm.delta || 0
  }
  try {
    await ElMessageBox.confirm(`确认调整共享库存池「${selectedCalendarPool.name || selectedCalendarPool.pool_code}」？`, '共享库存调整确认', { type: 'warning' })
  } catch {
    return
  }
  savingPoolAdjust.value = true
  try {
    await adjustInventoryPool(selectedCalendarPool.id, payload)
    ElMessage.success('共享库存池已调整')
    calendarCellDrawerVisible.value = false
    fetchCalendar()
    fetchPools()
  } finally {
    savingPoolAdjust.value = false
  }
}

onMounted(() => {
  fetchPools()
  searchProducts('')
})
</script>

<style lang="scss" scoped>
.filter-bar {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}

.inventory-tabs {
  :deep(.el-tabs__content) {
    overflow: visible;
  }
}

.stock-line {
  display: flex;
  gap: 12px;
  margin-bottom: 6px;
  font-size: 12px;
  color: var(--color-text-secondary);
}

.stock-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px 10px;
  width: 100%;
}

.stock-grid-item {
  display: grid;
  gap: 6px;
  min-width: 0;

  :deep(.el-input-number) {
    width: 100%;
  }

  :deep(.el-input__inner) {
    min-width: 0;
  }

  span {
    font-size: 12px;
    color: var(--color-text-placeholder);
    text-align: center;
  }
}

.form-tip {
  margin-top: 6px;
  font-size: 12px;
  color: var(--color-text-placeholder);

  &--error {
    color: #c45c4a;
  }
}

.binding-summary {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;

  div {
    padding: 12px;
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-small);
    background: var(--color-bg-warm);
  }

  span {
    display: block;
    margin-bottom: 6px;
    font-size: 12px;
    color: var(--color-text-placeholder);
  }

  strong {
    font-size: 20px;
  }
}

.drawer-note,
.text-secondary {
  font-size: 12px;
  color: var(--color-text-placeholder);
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
  padding-top: 16px;
  border-top: 1px solid var(--color-border-light);
}

.calendar-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 14px;
}

.calendar-legend {
  display: flex;
  align-items: center;
  gap: 18px;
  margin-bottom: 12px;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.legend-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  margin-right: 6px;
  border-radius: 50%;

  &--inventory {
    background: #4f8a72;
  }

  &--pool {
    background: #c8a872;
  }

  &--closed {
    background: #9aa0a6;
  }
}

.calendar-table {
  width: 100%;
}

.calendar-row-title {
  margin-bottom: 4px;
  color: var(--color-text-primary);
  font-weight: 600;
}

.calendar-cell {
  display: grid;
  width: 100%;
  min-width: 94px;
  min-height: 58px;
  padding: 8px;
  border: 1px solid rgba(79, 138, 114, 0.28);
  border-radius: var(--radius-small);
  background: rgba(79, 138, 114, 0.08);
  color: var(--color-text-primary);
  cursor: pointer;
  place-items: center;
  transition: all 0.18s ease;

  strong {
    font-size: 15px;
    line-height: 20px;
  }

  span {
    font-size: 11px;
    color: var(--color-text-secondary);
    line-height: 16px;
    white-space: nowrap;
  }

  em {
    padding: 1px 6px;
    border-radius: 999px;
    background: rgba(79, 138, 114, 0.12);
    color: var(--color-text-secondary);
    font-size: 11px;
    font-style: normal;
    line-height: 16px;
  }

  &:hover {
    border-color: rgba(79, 138, 114, 0.72);
    box-shadow: 0 6px 18px rgba(32, 55, 48, 0.12);
  }

  &--pool {
    border-color: rgba(200, 168, 114, 0.44);
    background: rgba(200, 168, 114, 0.12);
  }

  &--closed {
    border-color: rgba(154, 160, 166, 0.28);
    background: rgba(154, 160, 166, 0.09);
    color: var(--color-text-secondary);
  }

  &--today {
    border-color: #4080ff;
    box-shadow: inset 0 0 0 1px rgba(64, 128, 255, 0.32);
  }
}

:deep(.calendar-column--today) {
  background: #e8f3ff !important;
  color: #1d4ed8;
  font-weight: 700;
}

.cell-detail {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;

  div {
    min-height: 70px;
    padding: 12px;
    border: 1px solid var(--color-border-light);
    border-radius: var(--radius-small);
    background: var(--color-bg-warm);
  }

  span {
    display: block;
    margin-bottom: 6px;
    color: var(--color-text-placeholder);
    font-size: 12px;
  }

  strong {
    color: var(--color-text-primary);
    font-size: 15px;
    word-break: break-word;
  }
}

.drawer-actions {
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 768px) {
  .stock-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .calendar-toolbar {
    align-items: stretch;
    flex-direction: column;
  }

  .cell-detail {
    grid-template-columns: 1fr;
  }
}
</style>
