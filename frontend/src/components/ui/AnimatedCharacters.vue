<template>
  <div class="relative" style="width: 550px; height: 400px">
    <!-- Purple tall rectangle - Back layer -->
    <div
      ref="purpleRef"
      class="absolute bottom-0 transition-all duration-700 ease-in-out"
      :style="purpleStyle"
    >
      <div
        class="absolute flex gap-8 transition-all duration-700 ease-in-out"
        :style="purpleEyesStyle"
      >
        <!-- Purple eyes (with white eye balls) -->
        <div
          v-for="i in 2" :key="'pe'+i"
          class="rounded-full flex items-center justify-center transition-all duration-150"
          :style="{ width: '18px', height: isPurpleBlinking ? '2px' : '18px', backgroundColor: 'white', overflow: 'hidden' }"
        >
          <div
            v-if="!isPurpleBlinking"
            class="rounded-full"
            :style="{ width: '7px', height: '7px', backgroundColor: '#2D2D2D', transform: `translate(${purplePupilPos[i-1].x}px, ${purplePupilPos[i-1].y}px)`, transition: 'transform 0.1s ease-out' }"
          />
        </div>
      </div>
    </div>

    <!-- Black tall rectangle - Middle layer -->
    <div
      ref="blackRef"
      class="absolute bottom-0 transition-all duration-700 ease-in-out"
      :style="blackStyle"
    >
      <div
        class="absolute flex gap-6 transition-all duration-700 ease-in-out"
        :style="blackEyesStyle"
      >
        <div
          v-for="i in 2" :key="'be'+i"
          class="rounded-full flex items-center justify-center transition-all duration-150"
          :style="{ width: '16px', height: isBlackBlinking ? '2px' : '16px', backgroundColor: 'white', overflow: 'hidden' }"
        >
          <div
            v-if="!isBlackBlinking"
            class="rounded-full"
            :style="{ width: '6px', height: '6px', backgroundColor: '#2D2D2D', transform: `translate(${blackPupilPos[i-1].x}px, ${blackPupilPos[i-1].y}px)`, transition: 'transform 0.1s ease-out' }"
          />
        </div>
      </div>
    </div>

    <!-- Orange semi-circle - Front left -->
    <div
      ref="orangeRef"
      class="absolute bottom-0 transition-all duration-700 ease-in-out"
      :style="orangeStyle"
    >
      <div
        class="absolute flex gap-8 transition-all duration-200 ease-out"
        :style="orangeEyesStyle"
      >
        <div
          v-for="i in 2" :key="'oe'+i"
          class="rounded-full"
          :style="{ width: '12px', height: '12px', backgroundColor: '#2D2D2D', transform: `translate(${orangePupilPos[i-1].x}px, ${orangePupilPos[i-1].y}px)`, transition: 'transform 0.1s ease-out' }"
        />
      </div>
    </div>

    <!-- Yellow tall rectangle - Front right -->
    <div
      ref="yellowRef"
      class="absolute bottom-0 transition-all duration-700 ease-in-out"
      :style="yellowStyle"
    >
      <div
        class="absolute flex gap-6 transition-all duration-200 ease-out"
        :style="yellowEyesStyle"
      >
        <div
          v-for="i in 2" :key="'ye'+i"
          class="rounded-full"
          :style="{ width: '12px', height: '12px', backgroundColor: '#2D2D2D', transform: `translate(${yellowPupilPos[i-1].x}px, ${yellowPupilPos[i-1].y}px)`, transition: 'transform 0.1s ease-out' }"
        />
      </div>
      <div
        class="absolute w-20 h-[4px] bg-[#2D2D2D] rounded-full transition-all duration-200 ease-out"
        :style="yellowMouthStyle"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";

const props = defineProps({
  isTyping: { type: Boolean, default: false },
  showPassword: { type: Boolean, default: false },
  passwordLength: { type: Number, default: 0 },
});

// ── Mouse tracking ──────────────────────────────────────────────────────────
const mouseX = ref(0);
const mouseY = ref(0);

function handleMouseMove(e) {
  mouseX.value = e.clientX;
  mouseY.value = e.clientY;
}

onMounted(() => window.addEventListener("mousemove", handleMouseMove));
onBeforeUnmount(() => window.removeEventListener("mousemove", handleMouseMove));

// ── Refs ────────────────────────────────────────────────────────────────────
const purpleRef = ref(null);
const blackRef = ref(null);
const yellowRef = ref(null);
const orangeRef = ref(null);

// ── Blinking ────────────────────────────────────────────────────────────────
const isPurpleBlinking = ref(false);
const isBlackBlinking = ref(false);

let purpleBlinkTimer = null;
let blackBlinkTimer = null;

function schedulePurpleBlink() {
  const interval = Math.random() * 4000 + 3000;
  purpleBlinkTimer = setTimeout(() => {
    isPurpleBlinking.value = true;
    setTimeout(() => {
      isPurpleBlinking.value = false;
      schedulePurpleBlink();
    }, 150);
  }, interval);
}

function scheduleBlackBlink() {
  const interval = Math.random() * 4000 + 3000;
  blackBlinkTimer = setTimeout(() => {
    isBlackBlinking.value = true;
    setTimeout(() => {
      isBlackBlinking.value = false;
      scheduleBlackBlink();
    }, 150);
  }, interval);
}

onMounted(() => {
  schedulePurpleBlink();
  scheduleBlackBlink();
});

onBeforeUnmount(() => {
  clearTimeout(purpleBlinkTimer);
  clearTimeout(blackBlinkTimer);
});

// ── Looking at each other ──────────────────────────────────────────────────
const isLookingAtEachOther = ref(false);
let lookTimer = null;

watch(
  () => props.isTyping,
  (val) => {
    if (val) {
      isLookingAtEachOther.value = true;
      clearTimeout(lookTimer);
      lookTimer = setTimeout(() => {
        isLookingAtEachOther.value = false;
      }, 800);
    } else {
      isLookingAtEachOther.value = false;
    }
  }
);

onBeforeUnmount(() => clearTimeout(lookTimer));

// ── Purple peeking ─────────────────────────────────────────────────────────
const isPurplePeeking = ref(false);
let peekTimer = null;

function schedulePeek() {
  const interval = Math.random() * 3000 + 2000;
  peekTimer = setTimeout(() => {
    isPurplePeeking.value = true;
    setTimeout(() => {
      isPurplePeeking.value = false;
      schedulePeek();
    }, 800);
  }, interval);
}

watch(
  () => [props.passwordLength, props.showPassword],
  ([len, show]) => {
    clearTimeout(peekTimer);
    if (len > 0 && show) {
      schedulePeek();
    } else {
      isPurplePeeking.value = false;
    }
  },
  { immediate: true }
);

onBeforeUnmount(() => clearTimeout(peekTimer));

// ── Pupil position calculator (shared logic) ───────────────────────────────
function calcPupilPos(el, maxDist) {
  if (!el) return [0, 0];
  const rect = el.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 2;
  const dx = mouseX.value - cx;
  const dy = mouseY.value - cy;
  const dist = Math.min(Math.sqrt(dx * dx + dy * dy), maxDist);
  const angle = Math.atan2(dy, dx);
  return [Math.cos(angle) * dist, Math.sin(angle) * dist];
}

function makePupilPosObj(el, maxDist, forceX, forceY) {
  if (forceX !== undefined && forceY !== undefined) {
    return { x: forceX, y: forceY };
  }
  const [x, y] = calcPupilPos(el, maxDist);
  return { x, y };
}

// ── Force look directions ──────────────────────────────────────────────────
const showPwd = computed(() => props.passwordLength > 0 && props.showPassword);

const purpleForce = computed(() => {
  if (showPwd.value) return { x: isPurplePeeking.value ? 4 : -4, y: isPurplePeeking.value ? 5 : -4 };
  if (isLookingAtEachOther.value) return { x: 3, y: 4 };
  return {};
});
const blackForce = computed(() => {
  if (showPwd.value) return { x: -4, y: -4 };
  if (isLookingAtEachOther.value) return { x: 0, y: -4 };
  return {};
});
const orangeForce = computed(() => {
  if (showPwd.value) return { x: -5, y: -4 };
  return {};
});
const yellowForce = computed(() => {
  if (showPwd.value) return { x: -5, y: -4 };
  return {};
});

// Positioned pupil refs (using the eye container refs as fallback)
const purplePupilPos = computed(() => [makePupilPosObj(purpleRef.value, 5, purpleForce.value.x, purpleForce.value.y), makePupilPosObj(purpleRef.value, 5, purpleForce.value.x, purpleForce.value.y)]);
const blackPupilPos = computed(() => [makePupilPosObj(blackRef.value, 4, blackForce.value.x, blackForce.value.y), makePupilPosObj(blackRef.value, 4, blackForce.value.x, blackForce.value.y)]);
const orangePupilPos = computed(() => [makePupilPosObj(orangeRef.value, 5, orangeForce.value.x, orangeForce.value.y), makePupilPosObj(orangeRef.value, 5, orangeForce.value.x, orangeForce.value.y)]);
const yellowPupilPos = computed(() => [makePupilPosObj(yellowRef.value, 5, yellowForce.value.x, yellowForce.value.y), makePupilPosObj(yellowRef.value, 5, yellowForce.value.x, yellowForce.value.y)]);

// ── Position calculation ───────────────────────────────────────────────────
function calcPosition(el) {
  if (!el) return { faceX: 0, faceY: 0, bodySkew: 0 };
  const rect = el.getBoundingClientRect();
  const cx = rect.left + rect.width / 2;
  const cy = rect.top + rect.height / 3;
  const dx = mouseX.value - cx;
  const dy = mouseY.value - cy;
  return {
    faceX: Math.max(-15, Math.min(15, dx / 20)),
    faceY: Math.max(-10, Math.min(10, dy / 30)),
    bodySkew: Math.max(-6, Math.min(6, -dx / 120)),
  };
}

const purplePos = computed(() => calcPosition(purpleRef.value));
const blackPos = computed(() => calcPosition(blackRef.value));
const yellowPos = computed(() => calcPosition(yellowRef.value));
const orangePos = computed(() => calcPosition(orangeRef.value));

const isHidingPassword = computed(() => props.passwordLength > 0 && !props.showPassword);

// ── Styles ──────────────────────────────────────────────────────────────────
const purpleStyle = computed(() => {
  const baseHeight = (props.isTyping || isHidingPassword.value) ? "440px" : "400px";
  let skew = purplePos.value.bodySkew || 0;
  let tx = 0;
  if (showPwd.value) {
    skew = 0;
    tx = 0;
  } else if (props.isTyping || isHidingPassword.value) {
    skew = (purplePos.value.bodySkew || 0) - 12;
    tx = 40;
  }
  return {
    left: "70px",
    width: "180px",
    height: baseHeight,
    backgroundColor: "#6C3FF5",
    borderRadius: "10px 10px 0 0",
    zIndex: 1,
    transform: `skewX(${skew}deg) translateX(${tx}px)`,
    transformOrigin: "bottom center",
  };
});

const purpleEyesStyle = computed(() => ({
  left: showPwd.value ? "20px" : isLookingAtEachOther.value ? "55px" : `${45 + (purplePos.value.faceX || 0)}px`,
  top: showPwd.value ? "35px" : isLookingAtEachOther.value ? "65px" : `${40 + (purplePos.value.faceY || 0)}px`,
}));

const blackStyle = computed(() => {
  let skew = blackPos.value.bodySkew || 0;
  let tx = 0;
  if (showPwd.value) {
    skew = 0;
    tx = 0;
  } else if (isLookingAtEachOther.value) {
    skew = (blackPos.value.bodySkew || 0) * 1.5 + 10;
    tx = 20;
  } else if (props.isTyping || isHidingPassword.value) {
    skew = (blackPos.value.bodySkew || 0) * 1.5;
  }
  return {
    left: "240px",
    width: "120px",
    height: "310px",
    backgroundColor: "#2D2D2D",
    borderRadius: "8px 8px 0 0",
    zIndex: 2,
    transform: `skewX(${skew}deg) translateX(${tx}px)`,
    transformOrigin: "bottom center",
  };
});

const blackEyesStyle = computed(() => ({
  left: showPwd.value ? "10px" : isLookingAtEachOther.value ? "32px" : `${26 + (blackPos.value.faceX || 0)}px`,
  top: showPwd.value ? "28px" : isLookingAtEachOther.value ? "12px" : `${32 + (blackPos.value.faceY || 0)}px`,
}));

const orangeStyle = computed(() => ({
  left: "0px",
  width: "240px",
  height: "200px",
  zIndex: 3,
  backgroundColor: "#FF9B6B",
  borderRadius: "120px 120px 0 0",
  transform: `skewX(${showPwd.value ? 0 : (orangePos.value.bodySkew || 0)}deg)`,
  transformOrigin: "bottom center",
}));

const orangeEyesStyle = computed(() => ({
  left: showPwd.value ? "50px" : `${82 + (orangePos.value.faceX || 0)}px`,
  top: showPwd.value ? "85px" : `${90 + (orangePos.value.faceY || 0)}px`,
}));

const yellowStyle = computed(() => ({
  left: "310px",
  width: "140px",
  height: "230px",
  backgroundColor: "#E8D754",
  borderRadius: "70px 70px 0 0",
  zIndex: 4,
  transform: `skewX(${showPwd.value ? 0 : (yellowPos.value.bodySkew || 0)}deg)`,
  transformOrigin: "bottom center",
}));

const yellowEyesStyle = computed(() => ({
  left: showPwd.value ? "20px" : `${52 + (yellowPos.value.faceX || 0)}px`,
  top: showPwd.value ? "35px" : `${40 + (yellowPos.value.faceY || 0)}px`,
}));

const yellowMouthStyle = computed(() => ({
  left: showPwd.value ? "10px" : `${40 + (yellowPos.value.faceX || 0)}px`,
  top: showPwd.value ? "88px" : `${88 + (yellowPos.value.faceY || 0)}px`,
}));
</script>
