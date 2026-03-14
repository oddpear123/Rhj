<template>
  <div class="checkout-wrapper">
    <div v-if="loading" class="pulse-loader">
      Warming up the vault...
    </div>
    
    <div ref="checkoutRef" id="stripe-checkout" :class="{ 'is-loaded': !loading }"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted } from 'vue';
import { loadStripe } from '@stripe/stripe-js';
import { useAuthStore } from '../stores/auth.js';

const emit = defineEmits(['error']);

const props = defineProps({
  plan: {
    type: String,
    required: true
  }
});

const checkoutRef = ref(null);
const loading = ref(true);
let checkoutInstance = null;

onMounted(async () => {
  try {
    // 1. Wake up Stripe using your public test key
    const stripe = await loadStripe(import.meta.env.VITE_STRIPE_PUBLIC_KEY);
    const authStore = useAuthStore();

    // 2. Hit our FastAPI backend. This creates the Stripe Session securely
    // and returns the clientSecret we need to render the embedded UI.
    const response = await fetch(`${import.meta.env.VITE_API_URL}/subscription/create-embedded-checkout`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${authStore.token}`
      },
      body: JSON.stringify({ plan: props.plan })
    });

    if (!response.ok) throw new Error("Backend refused to open the checkout session.");
    
    const { clientSecret } = await response.json();

    // 3. Initialize the Embedded Checkout instance
    checkoutInstance = await stripe.initEmbeddedCheckout({
      clientSecret,
    });

    // 4. Mount it directly to our template ref. The fan never leaves the page.
    loading.value = false;
    checkoutInstance.mount(checkoutRef.value);

  } catch (error) {
    console.error("Payment initialization failed:", error);
    loading.value = false;
    emit('error', error.message || 'Payment initialization failed');
  }
});

// Clean up the iframe if the user clicks away before paying
onUnmounted(() => {
  if (checkoutInstance) {
    checkoutInstance.destroy();
  }
});
</script>

<style scoped>
.checkout-wrapper {
  width: 100%;
  max-width: 500px;
  margin: 0 auto;
  min-height: 400px;
  background-color: #111; /* Dark mode to match the dirty vibe */
  border-radius: 12px;
  padding: 1rem;
}

.pulse-loader {
  color: #ff3366; /* Hot pink accent */
  text-align: center;
  padding-top: 4rem;
  font-family: monospace;
  animation: pulse 1.5s infinite;
}

#stripe-checkout {
  opacity: 0;
  transition: opacity 0.4s ease-in;
}

#stripe-checkout.is-loaded {
  opacity: 1;
}

@keyframes pulse {
  0% { opacity: 0.6; }
  50% { opacity: 1; }
  100% { opacity: 0.6; }
}
</style>