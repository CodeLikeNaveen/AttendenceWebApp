/**
 * calendar.js
 * Renders the attendance calendar grid and powers the day-detail modal.
 * All data is injected by the Jinja2 template via window.__CAL_DATA__.
 */

(function () {
  "use strict";

  /* ── Data injected from server ─────────────────────────────── */
  const CAL = window.__CAL_DATA__ || {};
  const days = CAL.days || [];         // Array of CalendarDay objects
  const firstWeekday = CAL.firstWeekday || 0; // 0=Mon offset
  const today = CAL.today || "";
  const empCode = CAL.empCode || "";

  /* ── Colour class resolver ─────────────────────────────────── */
  function resolveClass(day) {
    if (day.is_sunday) return "att-sunday";
    if (day.is_holiday) return "att-holiday";
    if (day.on_leave) return "att-leave";

    const isFuture = day.date > today;
    if (isFuture) return "att-future";

    const v = day.attendance_value;
    if (v === null || v === undefined) return "att-none";
    if (v >= 1)     return "att-full";
    if (v >= 0.75)  return "att-three-q";
    if (v >= 0.5)   return "att-half";
    if (v >= 0.25)  return "att-quarter";
    if (v === 0)    return "att-absent";
    if (v < 0)      return "att-penalty";
    return "att-none";
  }

  /* ── Value display text ────────────────────────────────────── */
  function cellContent(day) {
    if (day.is_sunday)   return { icon: "—", label: "" };
    if (day.is_holiday)  return { icon: "✦", label: day.holiday_name ? day.holiday_name.substring(0, 5) : "H" };
    if (day.on_leave)    return { icon: "L", label: "" };

    const isFuture = day.date > today;
    if (isFuture)        return { icon: "", label: "" };

    const v = day.attendance_value;
    if (v === null || v === undefined) return { icon: "·", label: "" };
    return { icon: String(v), label: "" };
  }

  /* ── Build the calendar grid ───────────────────────────────── */
  function renderCalendar() {
    const grid = document.getElementById("calGrid");
    if (!grid) return;

    grid.innerHTML = "";

    // Empty offset cells for Mon–Sun alignment
    // firstWeekday: 0=Mon, 6=Sun
    for (let i = 0; i < firstWeekday; i++) {
      const empty = document.createElement("div");
      empty.className = "cal-cell empty";
      grid.appendChild(empty);
    }

    // Day cells
    days.forEach(function (day) {
      const cell = document.createElement("div");
      const cls = resolveClass(day);
      const isToday = day.date === today;
      cell.className = "cal-cell " + cls + (isToday ? " today" : "");
      cell.dataset.date = day.date;
      cell.setAttribute("role", "button");
      cell.setAttribute("tabindex", "0");

      const dayNum = parseInt(day.date.split("-")[2], 10);
      const { icon } = cellContent(day);

      cell.innerHTML =
        '<span class="cell-day">' + dayNum + "</span>" +
        '<span class="cell-val">' + icon + "</span>";

      // Click → open modal
      cell.addEventListener("click", function () {
        openDayModal(day);
      });
      cell.addEventListener("keydown", function (e) {
        if (e.key === "Enter" || e.key === " ") openDayModal(day);
      });

      grid.appendChild(cell);
    });
  }

  /* ── Modal ─────────────────────────────────────────────────── */
  function openDayModal(day) {
    const overlay = document.getElementById("dayModal");
    if (!overlay) return;

    // Title
    const d = new Date(day.date + "T00:00:00");
    const opts = { weekday: "long", day: "numeric", month: "long", year: "numeric" };
    document.getElementById("modalDateTitle").textContent =
      d.toLocaleDateString("en-IN", opts);

    // Status badge
    const badge = document.getElementById("modalBadge");
    badge.className = "modal-badge";
    let badgeText = "";
    let badgeBg = "";

    if (day.is_sunday) {
      badgeText = "☀️ Sunday"; badgeBg = "#e8edf3"; badge.style.color = "#374151";
    } else if (day.is_holiday) {
      badgeText = "✦ Holiday: " + (day.holiday_name || ""); badgeBg = "#dbeeff"; badge.style.color = "#1e40af";
    } else if (day.on_leave) {
      badgeText = "📋 " + (day.leave_type || "Leave"); badgeBg = "#ede9fe"; badge.style.color = "#5b21b6";
    } else {
      const v = day.attendance_value;
      if (v === null || v === undefined) {
        badgeText = "No Record"; badgeBg = "#f1f5f9"; badge.style.color = "#64748b";
      } else if (v >= 1) {
        badgeText = "✔ Full Day Present"; badgeBg = "#dcfce7"; badge.style.color = "#166534";
      } else if (v >= 0.75) {
        badgeText = "¾ Day Present"; badgeBg = "#bbf7d0"; badge.style.color = "#14532d";
      } else if (v >= 0.5) {
        badgeText = "½ Day Present"; badgeBg = "#fef9c3"; badge.style.color = "#713f12";
      } else if (v >= 0.25) {
        badgeText = "¼ Day Present"; badgeBg = "#ffedd5"; badge.style.color = "#7c2d12";
      } else if (v === 0) {
        badgeText = "✗ Absent"; badgeBg = "#fee2e2"; badge.style.color = "#991b1b";
      } else {
        badgeText = "⚠ Penalty"; badgeBg = "#fee2e2"; badge.style.color = "#7f1d1d";
      }
    }
    badge.textContent = badgeText;
    badge.style.background = badgeBg;

    // Detail rows
    setText("modalInTime",    day.in_time    || "—");
    setText("modalOutTime",   day.out_time   || "—");
    setText("modalWorked",    day.worked_hours || "—");
    setText("modalLateBy",    day.late_by    || "—");
    setText("modalEarlyBy",   day.early_by   || "—");

    // Comment
    const commentBox = document.getElementById("modalComment");
    if (day.comment) {
      commentBox.textContent = "💬 " + day.comment;
      commentBox.style.display = "block";
    } else {
      commentBox.style.display = "none";
    }

    // Leave info
    const leaveBox = document.getElementById("modalLeaveInfo");
    if (day.on_leave && day.leave_type) {
      leaveBox.textContent = "📋 Leave Type: " + day.leave_type;
      leaveBox.style.display = "block";
    } else {
      leaveBox.style.display = "none";
    }

    overlay.classList.add("active");
    document.body.style.overflow = "hidden";
  }

  function setText(id, val) {
    const el = document.getElementById(id);
    if (el) el.textContent = val;
  }

  function closeDayModal() {
    const overlay = document.getElementById("dayModal");
    if (overlay) overlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  /* ── Leave Application Modal ───────────────────────────────── */
  function openLeaveModal() {
    const overlay = document.getElementById("leaveModal");
    if (overlay) {
      overlay.classList.add("active");
      document.body.style.overflow = "hidden";
    }
  }

  function closeLeaveModal() {
    const overlay = document.getElementById("leaveModal");
    if (overlay) overlay.classList.remove("active");
    document.body.style.overflow = "";
  }

  /* ── Toast ─────────────────────────────────────────────────── */
  function showToast(msg, type) {
    const existing = document.querySelector(".toast");
    if (existing) existing.remove();

    const toast = document.createElement("div");
    toast.className = "toast toast-" + (type || "success");
    toast.textContent = msg;
    document.body.appendChild(toast);

    setTimeout(function () {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.3s";
      setTimeout(() => toast.remove(), 300);
    }, 4000);
  }

  /* ── URL param toasts ──────────────────────────────────────── */
  function checkUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.get("leave_success")) {
      showToast("✓ Leave application submitted successfully!", "success");
      // Clean URL
      window.history.replaceState({}, "", window.location.pathname);
    }
    if (params.get("leave_error")) {
      showToast("✗ " + decodeURIComponent(params.get("leave_error")), "error");
      window.history.replaceState({}, "", window.location.pathname);
    }
  }

  /* ── Init ──────────────────────────────────────────────────── */
  document.addEventListener("DOMContentLoaded", function () {
    renderCalendar();
    checkUrlParams();

    // Modal close buttons
    const closeDay = document.getElementById("closeDayModal");
    if (closeDay) closeDay.addEventListener("click", closeDayModal);

    const closeLeave = document.getElementById("closeLeaveModal");
    if (closeLeave) closeLeave.addEventListener("click", closeLeaveModal);

    // Close on overlay click
    document.getElementById("dayModal")?.addEventListener("click", function (e) {
      if (e.target === this) closeDayModal();
    });
    document.getElementById("leaveModal")?.addEventListener("click", function (e) {
      if (e.target === this) closeLeaveModal();
    });

    // Apply Leave button
    const applyBtn = document.getElementById("applyLeaveBtn");
    if (applyBtn) applyBtn.addEventListener("click", openLeaveModal);

    // ESC key
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") {
        closeDayModal();
        closeLeaveModal();
      }
    });
  });

  // Expose for inline handlers if needed
  window.closeDayModal = closeDayModal;
  window.closeLeaveModal = closeLeaveModal;
  window.openLeaveModal = openLeaveModal;
})();
