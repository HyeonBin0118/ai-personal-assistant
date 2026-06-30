const API_BASE = "";

// ---------- 공통 유틸 ----------

function getToken() {
  return localStorage.getItem("access_token");
}

function setToken(token) {
  localStorage.setItem("access_token", token);
}

function clearToken() {
  localStorage.removeItem("access_token");
}

function authHeaders() {
  return { Authorization: `Bearer ${getToken()}` };
}

function requireAuthOrRedirect() {
  if (!getToken()) {
    window.location.href = "/static/login.html";
  }
}

// ---------- 로그인 페이지 ----------

function initLoginPage() {
  // 이미 로그인되어 있으면 메인으로
  if (getToken()) {
    window.location.href = "/static/index.html";
    return;
  }

  let mode = "login"; // "login" | "signup"

  const form = document.getElementById("authForm");
  const emailInput = document.getElementById("email");
  const passwordInput = document.getElementById("password");
  const submitBtn = document.getElementById("submitBtn");
  const toggleBtn = document.getElementById("toggleModeBtn");
  const errorMsg = document.getElementById("errorMsg");
  const formTitle = document.getElementById("formTitle");
  const formSubtitle = document.getElementById("formSubtitle");

  toggleBtn.addEventListener("click", () => {
    mode = mode === "login" ? "signup" : "login";
    errorMsg.textContent = "";
    if (mode === "login") {
      formTitle.textContent = "로그인";
      formSubtitle.textContent = "일상을 말하면 비서가 정리해드려요";
      submitBtn.textContent = "로그인";
      toggleBtn.textContent = "계정이 없으신가요? 회원가입";
    } else {
      formTitle.textContent = "회원가입";
      formSubtitle.textContent = "이메일과 비밀번호로 간단하게 시작해요";
      submitBtn.textContent = "회원가입";
      toggleBtn.textContent = "이미 계정이 있으신가요? 로그인";
    }
  });

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    errorMsg.textContent = "";
    submitBtn.disabled = true;

    const email = emailInput.value.trim();
    const password = passwordInput.value;

    try {
      if (mode === "signup") {
        const res = await fetch(`${API_BASE}/auth/signup`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
        });
        if (!res.ok) {
          const data = await res.json().catch(() => ({}));
          throw new Error(data.detail || "회원가입에 실패했어요");
        }
        // 가입 성공 후 바로 로그인 처리
        await loginRequest(email, password);
      } else {
        await loginRequest(email, password);
      }
      window.location.href = "/static/index.html";
    } catch (err) {
      errorMsg.textContent = err.message;
    } finally {
      submitBtn.disabled = false;
    }
  });

  async function loginRequest(email, password) {
    const body = new URLSearchParams();
    body.set("username", email);
    body.set("password", password);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body,
    });
    if (!res.ok) {
      const data = await res.json().catch(() => ({}));
      throw new Error(data.detail || "이메일 또는 비밀번호가 올바르지 않아요");
    }
    const data = await res.json();
    setToken(data.access_token);
  }
}

// ---------- 메인 페이지 ----------

function initMainPage() {
  requireAuthOrRedirect();

  const logoutBtn = document.getElementById("logoutBtn");
  const inputText = document.getElementById("inputText");
  const sendBtn = document.getElementById("sendBtn");
  const itemList = document.getElementById("itemList");
  const tabBtns = document.querySelectorAll(".tab-btn");
  const notificationBanner = document.getElementById("notificationBanner");

  let currentTab = "schedules";

  logoutBtn.addEventListener("click", () => {
    clearToken();
    window.location.href = "/static/login.html";
  });

  tabBtns.forEach((btn) => {
    btn.addEventListener("click", () => {
      tabBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      currentTab = btn.dataset.tab;
      loadList(currentTab);
    });
  });

  sendBtn.addEventListener("click", submitInput);
  inputText.addEventListener("keydown", (e) => {
    if (e.key === "Enter") submitInput();
  });

  async function submitInput() {
    const text = inputText.value.trim();
    if (!text) return;

    sendBtn.disabled = true;
    sendBtn.textContent = "처리 중...";

    try {
      const res = await fetch(`${API_BASE}/input`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...authHeaders(),
        },
        body: JSON.stringify({ text }),
      });

      if (res.status === 401) {
        clearToken();
        window.location.href = "/static/login.html";
        return;
      }

      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        throw new Error(data.detail || "처리에 실패했어요");
      }

      const data = await res.json();
      inputText.value = "";
      showNotification(data.message);

      // 등록된 카테고리 탭으로 자동 전환 후 새로고침
      tabBtns.forEach((b) => b.classList.remove("active"));
      const matchedTab = document.querySelector(`.tab-btn[data-tab="${data.category}s"]`);
      if (matchedTab) {
        matchedTab.classList.add("active");
        currentTab = `${data.category}s`;
      }
      loadList(currentTab);
    } catch (err) {
      showNotification(err.message);
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = "등록";
    }
  }

  function showNotification(message) {
    notificationBanner.textContent = message;
    notificationBanner.classList.add("visible");
    setTimeout(() => {
      notificationBanner.classList.remove("visible");
    }, 4000);
  }

  async function loadList(tab) {
    itemList.innerHTML = `<p class="empty-msg">불러오는 중...</p>`;

    try {
      const res = await fetch(`${API_BASE}/${tab}`, {
        headers: authHeaders(),
      });

      if (res.status === 401) {
        clearToken();
        window.location.href = "/static/login.html";
        return;
      }

      const data = await res.json();
      renderList(tab, data);
    } catch (err) {
      itemList.innerHTML = `<p class="empty-msg">불러오기에 실패했어요</p>`;
    }
  }

  function renderList(tab, items) {
    if (!items || items.length === 0) {
      itemList.innerHTML = `<p class="empty-msg">아직 등록된 항목이 없어요</p>`;
      return;
    }

    itemList.innerHTML = items
      .map((item) => {
        if (tab === "schedules") {
          return `
            <div class="item-card">
              <div>
                <div>${escapeHtml(item.title)}</div>
                <div class="meta">${formatDate(item.start_at)}</div>
              </div>
              <span class="badge">${statusLabel(item.status)}</span>
            </div>`;
        } else if (tab === "expenses") {
          return `
            <div class="item-card">
              <div>
                <div>${escapeHtml(item.item)}</div>
                <div class="meta">${formatDate(item.occurred_at)}</div>
              </div>
              <span class="badge">${item.amount.toLocaleString()}원</span>
            </div>`;
        } else {
          return `
            <div class="item-card">
              <div>
                <div>${escapeHtml(item.content)}</div>
                <div class="meta">${formatDate(item.created_at)}</div>
              </div>
              <span class="badge">${item.is_done ? "완료" : "진행중"}</span>
            </div>`;
        }
      })
      .join("");
  }

  function statusLabel(status) {
    const map = { pending: "예정", completed: "완료", cancelled: "취소" };
    return map[status] || status;
  }

  function formatDate(isoString) {
    const d = new Date(isoString);
    return d.toLocaleString("ko-KR", {
      month: "long",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }

  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- 알림 폴링 ----------

  async function pollNotifications() {
    try {
      const res = await fetch(`${API_BASE}/notifications?unread_only=true`, {
        headers: authHeaders(),
      });
      if (!res.ok) return;

      const notifications = await res.json();
      if (notifications.length > 0) {
        const latest = notifications[0];
        showNotification(latest.message);
        markAsRead(latest.id);
      }
    } catch (err) {
      // 폴링 실패는 조용히 무시 (다음 주기에 재시도)
    }
  }

  async function markAsRead(notificationId) {
    try {
      await fetch(`${API_BASE}/notifications/${notificationId}/read`, {
        method: "PATCH",
        headers: authHeaders(),
      });
    } catch (err) {
      // 무시
    }
  }

  setInterval(pollNotifications, 15000); // 15초마다 폴링
  pollNotifications();

  // 초기 로딩
  loadList(currentTab);
}