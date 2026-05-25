function getPageName() {
  return document.body.dataset.page || location.pathname.split('/').pop().replace('.html','') || 'home';
}
function navTo(page) { window.location.href = page + '.html'; }
function navBack() {
  if (history.length > 1) history.back();
  else window.location.href = 'home.html';
}
function showToast(message) {
  const toast = document.getElementById('toast');
  if (!toast) return alert(message);
  toast.textContent = message;
  toast.classList.add('show');
  setTimeout(() => toast.classList.remove('show'), 2000);
}
let bannerIndex = 0;
function autoBanner() {
  const banner = document.getElementById('banner');
  if (!banner) return;
  const dots = document.querySelectorAll('.banner-dot');
  bannerIndex = (bannerIndex + 1) % 3;
  banner.style.transform = `translateX(-${bannerIndex * 100}%)`;
  dots.forEach((dot, i) => dot.classList.toggle('active', i === bannerIndex));
}
let codeTimer = null;
function sendCode() {
  const phone = document.getElementById('login-phone')?.value || '';
  if (!phone || phone.length !== 11) return showToast('请输入正确的手机号');
  const btn = document.getElementById('send-code-btn');
  if (!btn) return;
  btn.disabled = true; btn.classList.add('opacity-50');
  let seconds = 60; btn.textContent = `${seconds}s`;
  codeTimer = setInterval(() => {
    seconds--;
    if (seconds <= 0) { clearInterval(codeTimer); btn.disabled = false; btn.classList.remove('opacity-50'); btn.textContent = '获取验证码'; }
    else btn.textContent = `${seconds}s`;
  }, 1000);
  showToast('验证码已发送');
}
function doLogin() {
  const phone = document.getElementById('login-phone')?.value || '';
  const code = document.getElementById('login-code')?.value || '';
  if (!phone || phone.length !== 11) return showToast('请输入正确的手机号');
  if (!code || code.length !== 6) return showToast('请输入验证码');
  showToast('登录成功'); setTimeout(() => navTo('home'), 1000);
}
function showRepairModal() { const wrap=document.getElementById('repair-modal'); if(!wrap) return; wrap.classList.remove('hidden'); setTimeout(()=>wrap.querySelector('.modal')?.classList.add('show'),10); }
function hideRepairModal() { const wrap=document.getElementById('repair-modal'); if(!wrap) return; wrap.querySelector('.modal')?.classList.remove('show'); setTimeout(()=>wrap.classList.add('hidden'),300); }
function submitRepair() { hideRepairModal(); showToast('报修提交成功'); }
function showRepairDetail(title, status) {
  const t=document.getElementById('detail-title'); if(t) t.textContent=title;
  const statusEl=document.getElementById('detail-status');
  if(statusEl){ statusEl.textContent=status; statusEl.className='px-3 py-1 text-sm rounded';
    if(status==='处理中') statusEl.classList.add('bg-yellow-100','text-yellow-600');
    else if(status==='已完成') statusEl.classList.add('bg-green-100','text-green-600');
    else if(status==='已撤回') statusEl.classList.add('bg-gray-100','text-gray-600'); }
  const withdrawBtn=document.getElementById('withdraw-btn-container'); if(withdrawBtn) withdrawBtn.style.display = status==='已撤回'||status==='已完成' ? 'none':'block';
  const wrap=document.getElementById('repair-detail-modal'); if(!wrap) return; wrap.classList.remove('hidden'); setTimeout(()=>wrap.querySelector('.modal')?.classList.add('show'),10);
}
function hideRepairDetailModal() { const wrap=document.getElementById('repair-detail-modal'); if(!wrap) return; wrap.querySelector('.modal')?.classList.remove('show'); setTimeout(()=>wrap.classList.add('hidden'),300); }
function withdrawRepair() { hideRepairDetailModal(); showToast('报修已撤回'); }
function updatePayTotal() {
  let total=0,count=0;
  document.querySelectorAll('.pay-checkbox:checked').forEach(cb=>{ const amountInput=cb.closest('.p-4')?.querySelector('.pay-amount'); let amount=parseFloat(amountInput?.value)||0; if(amount<10) amount=10; total+=amount; count++; });
  const set=(id,v)=>{ const el=document.getElementById(id); if(el) el.textContent=v; };
  set('pay-total', total.toFixed(2)); set('pay-count', count); set('pay-btn-total', total.toFixed(2));
}
function doPay() { if(document.querySelectorAll('.pay-checkbox:checked').length===0) return showToast('请至少选择一项费用'); showToast('跳转支付...'); }
document.addEventListener('DOMContentLoaded', () => {
  const page=getPageName();
  document.querySelectorAll('.tab-btn').forEach(btn=>btn.classList.toggle('active', btn.dataset.page===page));
  document.querySelectorAll('.pay-checkbox').forEach(cb=>cb.addEventListener('change', updatePayTotal));
  document.querySelectorAll('.pay-amount').forEach(input=>input.addEventListener('input', function(){ if(parseFloat(this.value)<10){ this.value=10; showToast('最低金额不能低于 10 元'); } updatePayTotal(); }));
  updatePayTotal(); autoBanner(); if(document.getElementById('banner')) setInterval(autoBanner,3000);
});
