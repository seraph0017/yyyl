<template>
  <view class="page-service">
    <view class="service-hero">
      <text class="service-hero__title">智能客服</text>
      <text class="service-hero__subtitle">一月一露营地咨询</text>
    </view>

    <view class="quick-section">
      <scroll-view scroll-x class="quick-scroll" :show-scrollbar="false">
        <view class="quick-list">
          <view class="quick-chip" v-for="item in categories" :key="item.id" @tap="onCategoryTap(item.name)">
            <text class="quick-chip__icon">{{ item.icon }}</text>
            <text>{{ item.name }}</text>
          </view>
        </view>
      </scroll-view>
    </view>

    <scroll-view class="chat-panel" scroll-y :scroll-into-view="lastMessageAnchor" scroll-with-animation>
      <view
        v-for="message in chatMessages"
        :id="`msg-${message.id}`"
        :key="message.id"
        class="chat-message"
        :class="message.role === 'user' ? 'chat-message--user' : 'chat-message--assistant'"
      >
        <view class="chat-bubble">
          <text>{{ message.content }}</text>
        </view>

        <view v-if="message.role === 'assistant'" class="assistant-meta">
          <view v-if="message.sources.length > 0" class="source_refs">
            <text class="assistant-meta__label">来源引用</text>
            <view class="source_refs__list">
              <text v-for="source in message.sources" :key="source.id" class="source_refs__item">
                {{ source.title }}
              </text>
            </view>
          </view>
          <view v-if="message.needs_human" class="human-fallback">
            <text>已转人工客服确认</text>
          </view>
          <view v-if="message.log_id && !message.feedback" class="feedback-row">
            <text>这个回答有帮助吗？</text>
            <view class="feedback-row__actions">
              <text @tap="submitFeedback(message, 'helpful')">{{ message.feedbackSubmitting ? '提交中' : '有用' }}</text>
              <text @tap="submitFeedback(message, 'unhelpful')">{{ message.feedbackSubmitting ? '提交中' : '无用' }}</text>
            </view>
          </view>
          <view v-if="message.feedback" class="feedback-done">
            <text>已记录反馈</text>
          </view>
        </view>
      </view>
      <view id="chat-bottom" class="chat-bottom"></view>
    </scroll-view>

    <view class="hot-section" v-if="hotQuestions.length > 0">
      <text class="hot-section__title">热门问题</text>
      <view class="hot-list">
        <view class="hot-item" v-for="item in hotQuestions" :key="item.id" @tap="sendFaqQuestion(item)">
          <text>{{ item.question }}</text>
        </view>
      </view>
    </view>

    <view class="human-service">
      <view class="human-service__info">
        <text class="human-service__title">人工客服</text>
        <text class="human-service__hours">{{ serviceHours }}</text>
      </view>
      <view class="human-service__actions">
        <button class="human-service__btn" @tap="onCallPhone">电话</button>
        <button class="human-service__btn" @tap="onCopyWechat">微信</button>
      </view>
    </view>

    <view class="input-bar">
      <input
        class="input-bar__field"
        placeholder="输入问题"
        :value="currentQuestion"
        confirm-type="send"
        :disabled="asking"
        @input="onQuestionInput"
        @confirm="sendQuestion()"
      />
      <button class="input-bar__send" :disabled="asking || !currentQuestion.trim()" @tap="sendQuestion()">
        {{ asking ? '发送中' : '发送' }}
      </button>
    </view>
  </view>
</template>

<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { onLoad } from '@dcloudio/uni-app'
import { get, post } from '@/utils/request'
import type {
  ICustomerServiceAskResult,
  ICustomerServiceSource,
  IFaqCategory,
  IFaqItem,
} from '@/types'

interface FaqItem {
  id: number
  question: string
  answer: string
}

interface ChatMessage {
  id: number
  role: 'user' | 'assistant'
  content: string
  sources: ICustomerServiceSource[]
  needs_human: boolean
  log_id?: number
  feedback_token?: string
  fallback_answer?: string
  feedback?: 'helpful' | 'unhelpful'
  feedbackSubmitting?: boolean
}

const currentQuestion = ref('')
const categories = ref<{ id: number; name: string; icon: string }[]>([])
const hotQuestions = ref<FaqItem[]>([])
const chatMessages = ref<ChatMessage[]>([])
const asking = ref(false)
const lastMessageAnchor = ref('')
const servicePhone = ref('400-888-1234')
const serviceWechat = ref('yyyl_service')
const serviceHours = ref('09:00 - 21:00')
let messageId = 0

onLoad(() => {
  chatMessages.value.push({
    id: nextMessageId(),
    role: 'assistant',
    content: '你好，请直接输入要咨询的问题。',
    sources: [],
    needs_human: false,
  })
  loadFaqData()
})

async function loadFaqData() {
  try {
    const data = await get<IFaqCategory[]>('/faq/categories', undefined, { needAuth: false })
    if (data && data.length > 0) {
      categories.value = data.map(c => ({ id: c.id, name: c.name, icon: c.icon || '问' }))
      const allItems: FaqItem[] = []
      data.forEach(cat => {
        cat.items?.forEach((item: IFaqItem) => {
          allItems.push({ id: item.id, question: item.question, answer: item.answer })
        })
      })
      hotQuestions.value = allItems.slice(0, 4)
      return
    }
  } catch {
    // FAQ 只作为快捷入口，失败不影响智能问答主链路。
  }

  categories.value = [
    { id: 1, name: '预定问题', icon: '订' },
    { id: 2, name: '退款规则', icon: '退' },
    { id: 3, name: '营地交通', icon: '行' },
    { id: 4, name: '会员权益', icon: '卡' },
  ]
}

function onQuestionInput(e: any) {
  currentQuestion.value = e.detail.value
}

async function sendQuestion(rawQuestion?: string, fallbackAnswer?: string) {
  const question = (rawQuestion ?? currentQuestion.value).trim()
  if (!question || asking.value) return

  chatMessages.value.push({
    id: nextMessageId(),
    role: 'user',
    content: question,
    sources: [],
    needs_human: false,
  })
  currentQuestion.value = ''
  scrollToBottom()

  asking.value = true
  try {
    const result = await post<ICustomerServiceAskResult>(
      '/customer-service/ask',
      { question },
      { needAuth: false, showError: false },
    )
    chatMessages.value.push({
      id: nextMessageId(),
      role: 'assistant',
      content: result.needs_human && fallbackAnswer ? fallbackAnswer : result.answer,
      sources: result.sources || [],
      needs_human: result.needs_human && !fallbackAnswer,
      log_id: result.log_id,
      feedback_token: result.feedback_token,
      fallback_answer: fallbackAnswer,
    })
  } catch (err: any) {
    chatMessages.value.push({
      id: nextMessageId(),
      role: 'assistant',
      content: fallbackAnswer || err?.message || '客服暂时无法回答，已为你转到人工客服。',
      sources: [],
      needs_human: !fallbackAnswer,
    })
  } finally {
    asking.value = false
    scrollToBottom()
  }
}

async function submitFeedback(message: ChatMessage, feedback: 'helpful' | 'unhelpful') {
  if (!message.log_id || !message.feedback_token || message.feedbackSubmitting) return
  message.feedbackSubmitting = true
  try {
    await post(
      `/customer-service/ask-logs/${message.log_id}/feedback`,
      { feedback, feedback_token: message.feedback_token },
      { needAuth: false, showError: false },
    )
    message.feedback = feedback
  } catch {
    uni.showToast({ title: '反馈提交失败', icon: 'none' })
  } finally {
    message.feedbackSubmitting = false
  }
}

function sendFaqQuestion(item: FaqItem) {
  sendQuestion(item.question, item.answer)
}

function onCategoryTap(name: string) {
  sendQuestion(`${name}怎么处理？`)
}

function onCallPhone() {
  uni.makePhoneCall({ phoneNumber: servicePhone.value })
}

function onCopyWechat() {
  uni.setClipboardData({
    data: serviceWechat.value,
    success: () => uni.showToast({ title: '微信号已复制', icon: 'success' }),
  })
}

function nextMessageId() {
  messageId += 1
  return messageId
}

function scrollToBottom() {
  lastMessageAnchor.value = ''
  nextTick(() => {
    if (chatMessages.value.length > 0) {
      lastMessageAnchor.value = `msg-${chatMessages.value[chatMessages.value.length - 1].id}`
    } else {
      lastMessageAnchor.value = 'chat-bottom'
    }
  })
}
</script>

<style lang="scss" scoped>
.page-service {
  min-height: 100vh;
  padding-bottom: 140rpx;
  background: #f5f3ee;
}

.service-hero {
  padding: 34rpx 28rpx 24rpx;
  background: linear-gradient(135deg, #2d4a3e 0%, #456852 100%);
  color: #fff;

  &__title {
    display: block;
    font-size: 38rpx;
    font-weight: 700;
  }

  &__subtitle {
    display: block;
    margin-top: 8rpx;
    color: rgba(255, 255, 255, 0.78);
    font-size: 24rpx;
  }
}

.quick-section {
  padding: 18rpx 0 12rpx;
  background: #fff;
}

.quick-scroll {
  white-space: nowrap;
}

.quick-list {
  display: inline-flex;
  gap: 14rpx;
  padding: 0 24rpx;
}

.quick-chip {
  display: inline-flex;
  align-items: center;
  gap: 8rpx;
  height: 88rpx;
  padding: 0 24rpx;
  border-radius: 44rpx;
  background: #eef4ef;
  color: #2d4a3e;
  font-size: 24rpx;

  &__icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 34rpx;
    height: 34rpx;
    border-radius: 50%;
    background: #c8a872;
    color: #fff;
    font-size: 20rpx;
  }
}

.chat-panel {
  height: 54vh;
  padding: 22rpx 24rpx;
  box-sizing: border-box;
}

.chat-message {
  display: flex;
  flex-direction: column;
  margin-bottom: 22rpx;

  &--user {
    align-items: flex-end;

    .chat-bubble {
      background: #2d4a3e;
      color: #fff;
      border-bottom-right-radius: 8rpx;
    }
  }

  &--assistant {
    align-items: flex-start;

    .chat-bubble {
      background: #fff;
      color: #26342d;
      border-bottom-left-radius: 8rpx;
    }
  }
}

.chat-bubble {
  max-width: 82%;
  padding: 20rpx 24rpx;
  border-radius: 24rpx;
  box-shadow: 0 8rpx 22rpx rgba(45, 74, 62, 0.08);
  line-height: 1.7;
  font-size: 28rpx;
  word-break: break-word;
}

.assistant-meta {
  max-width: 86%;
  margin-top: 10rpx;
  color: #6d756f;
  font-size: 22rpx;
}

.assistant-meta__label {
  display: block;
  margin-bottom: 8rpx;
  color: #2d4a3e;
  font-weight: 600;
}

.source_refs__list {
  display: flex;
  flex-wrap: wrap;
  gap: 8rpx;
}

.source_refs__item {
  max-width: 100%;
  padding: 6rpx 12rpx;
  border-radius: 6rpx;
  background: #e9f1eb;
  color: #2d4a3e;
  word-break: break-word;
}

.human-fallback {
  margin-top: 8rpx;
  color: #9a6a1f;
}

.feedback-row,
.feedback-done {
  display: flex;
  align-items: center;
  gap: 14rpx;
  margin-top: 12rpx;
}

.feedback-row__actions {
  display: flex;
  gap: 12rpx;
  min-height: 88rpx;
  align-items: center;

  text {
    min-width: 88rpx;
    height: 64rpx;
    line-height: 64rpx;
    padding: 0 18rpx;
    border-radius: 32rpx;
    background: #fff;
    color: #2d4a3e;
  }
}

.chat-bottom {
  height: 8rpx;
}

.hot-section {
  margin: 0 24rpx 18rpx;
  padding: 20rpx;
  border-radius: 8rpx;
  background: #fff;

  &__title {
    display: block;
    margin-bottom: 14rpx;
    color: #26342d;
    font-size: 26rpx;
    font-weight: 700;
  }
}

.hot-list {
  display: flex;
  flex-direction: column;
  gap: 10rpx;
}

.hot-item {
  padding: 18rpx;
  border-radius: 8rpx;
  background: #faf6f0;
  color: #3d453f;
  font-size: 26rpx;
}

.human-service {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 18rpx;
  margin: 0 24rpx 18rpx;
  padding: 22rpx;
  border-radius: 8rpx;
  background: #fff;

  &__info {
    min-width: 0;
  }

  &__title {
    display: block;
    color: #26342d;
    font-weight: 700;
    font-size: 28rpx;
  }

  &__hours {
    display: block;
    margin-top: 6rpx;
    color: #7d837f;
    font-size: 22rpx;
  }

  &__actions {
    display: flex;
    gap: 10rpx;
  }

  &__btn {
    width: 104rpx;
    height: 88rpx;
    line-height: 88rpx;
    padding: 0;
    border-radius: 44rpx;
    background: #2d4a3e;
    color: #fff;
    font-size: 24rpx;
  }
}

.input-bar {
  position: fixed;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  align-items: center;
  gap: 14rpx;
  padding: 18rpx 24rpx calc(18rpx + env(safe-area-inset-bottom));
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 -8rpx 28rpx rgba(45, 74, 62, 0.08);
  box-sizing: border-box;

  &__field {
    flex: 1;
    height: 88rpx;
    padding: 0 24rpx;
    border-radius: 44rpx;
    background: #f0f3ef;
    color: #26342d;
    font-size: 28rpx;
  }

  &__send {
    width: 132rpx;
    height: 88rpx;
    line-height: 88rpx;
    padding: 0;
    border-radius: 44rpx;
    background: #c8a872;
    color: #fff;
    font-size: 26rpx;

    &[disabled] {
      background: #c9cdc8;
      color: #fff;
    }
  }
}
</style>
