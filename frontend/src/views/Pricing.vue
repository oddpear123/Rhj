<template>
  <div class="pricing-page">
    <!-- Embedded checkout mode: hide plan cards, show checkout inline -->
    <template v-if="selectedPlan">
      <h1>Complete Your Purchase</h1>
      <p class="pricing-sub">{{ selectedPlanLabel }}</p>
      <StripeCheckout :plan="selectedPlan" @error="handleCheckoutError" />
      <button class="btn-secondary back-btn" @click="selectedPlan = null">Back to Plans</button>
    </template>

    <!-- Plan selection mode -->
    <template v-else>
      <h1>Unlock Full Access</h1>
      <p class="pricing-sub">Get unlimited access to all full-resolution photos</p>

      <div class="plans">
        <div class="plan-card card" v-for="plan in plans" :key="plan.id" :class="{ featured: plan.featured }">
          <div v-if="plan.badge" class="badge">{{ plan.badge }}</div>
          <h2>{{ plan.name }}</h2>
          <div class="price">{{ plan.price }}</div>
          <div class="price-detail">{{ plan.detail }}</div>
          <div v-if="auth.isAdmin" class="already-sub">
            <p>Admin — full access granted</p>
            <router-link to="/gallery" class="btn-secondary btn-block">Go to Gallery</router-link>
          </div>
          <div v-else-if="auth.isSubscribed" class="already-sub">
            <p>You're subscribed!</p>
            <router-link to="/gallery" class="btn-secondary btn-block">Go to Gallery</router-link>
          </div>
          <button
            v-else-if="auth.isLoggedIn"
            @click="handleCheckout(plan.id)"
            class="btn-primary btn-block"
          >
            Subscribe Now
          </button>
          <router-link v-else to="/register" class="btn-primary btn-block">
            Sign Up to Subscribe
          </router-link>
        </div>
      </div>

      <p v-if="checkoutError" class="error-msg checkout-error">{{ checkoutError }}</p>

      <ul class="features-global">
        <li>Full-resolution photo downloads</li>
        <li>Access to entire gallery</li>
        <li>New content added regularly</li>
        <li>Cancel anytime</li>
      </ul>
    </template>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useAuthStore } from '../stores/auth.js'
import StripeCheckout from './StripeCheckout.vue'

const auth = useAuthStore()

const selectedPlan = ref(null)
const checkoutError = ref('')

function handleCheckout(planId) {
  checkoutError.value = ''
  selectedPlan.value = planId
}

function handleCheckoutError(msg) {
  checkoutError.value = msg
  selectedPlan.value = null
}

const selectedPlanLabel = computed(() => {
  const plan = plans.find(p => p.id === selectedPlan.value)
  return plan ? `${plan.name} — ${plan.price}` : ''
})

const plans = [
  {
    id: '1month',
    name: '1 Month',
    price: '$16',
    detail: 'per month',
    badge: null,
    featured: false,
  },
  {
    id: '3month',
    name: '3 Months',
    price: '$36',
    detail: '$12/mo — save 25%',
    badge: '25% OFF',
    featured: true,
  },
]
</script>

<style scoped>
.pricing-page{text-align:center;padding-top:2rem}
.pricing-page h1{font-size:2.2rem;margin-bottom:.5rem}
.pricing-sub{color:#888;margin-bottom:2.5rem;font-size:1.1rem}

.plans{display:grid;grid-template-columns:repeat(2, 1fr);gap:1.5rem;max-width:600px;margin:0 auto}

.plan-card{text-align:center;position:relative;transition:transform .2s, border-color .2s}
.plan-card:hover{transform:translateY(-4px)}
.plan-card.featured{border-color:#e74c3c}

.badge{position:absolute;top:-12px;left:50%;transform:translateX(-50%);background:#e74c3c;color:#fff;padding:.25rem .75rem;border-radius:20px;font-size:.75rem;font-weight:700;white-space:nowrap}

.plan-card h2{font-size:1.1rem;margin-bottom:.75rem;color:#ccc}
.price{font-size:2.2rem;font-weight:800;color:#e74c3c;margin-bottom:.25rem}
.price-detail{color:#888;font-size:.85rem;margin-bottom:1.5rem}

.btn-block{width:100%;text-align:center;display:block}

.already-sub{text-align:center}
.already-sub p{color:#2ecc71;margin-bottom:1rem;font-weight:600}

.checkout-error{text-align:center;margin-top:1.5rem}

.back-btn{margin-top:1.5rem;display:inline-block}

.features-global{list-style:none;max-width:600px;margin:2.5rem auto 0;text-align:left}
.features-global li{padding:.5rem 0;border-bottom:1px solid #222;color:#ccc;font-size:.95rem}
.features-global li::before{content:"+ ";color:#2ecc71;font-weight:700}
</style>
