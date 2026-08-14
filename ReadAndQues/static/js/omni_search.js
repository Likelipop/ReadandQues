document.addEventListener('DOMContentLoaded', function() {
    const omniContainer = document.getElementById('omni-search-container');
    const input = document.getElementById('omni-input');
    const spinner = document.getElementById('omni-spinner');
    const toast = document.getElementById('omni-toast');
    const dropdown = document.getElementById('omni-dropdown');
    const resultsList = document.getElementById('omni-results-list');
    const toggleContainer = document.getElementById('search-mode-toggle');
    const btnBm25 = document.getElementById('btn-mode-bm25');
    const btnAi = document.getElementById('btn-mode-ai');
    const icon = document.getElementById('omni-icon');

    if (!input) return;

    // State
    let searchMode = 'bm25'; // 'bm25' or 'ai'
    let typingTimer;
    const typingInterval = 400;

    function isUrl(text) {
        return /^(https?:\/\/)/i.test(text) || /^www\./i.test(text);
    }

    // Toggle logic
    function setMode(mode) {
        searchMode = mode;
        if (btnBm25 && btnAi) {
            if (mode === 'bm25') {
                btnBm25.className = 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-blue-100 text-blue-700 transition';
                btnAi.className = 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-transparent text-slate-500 hover:bg-slate-100 transition';
            } else {
                btnAi.className = 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-indigo-100 text-indigo-700 transition';
                btnBm25.className = 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-transparent text-slate-500 hover:bg-slate-100 transition';
            }
        }
        if (input.value.trim() && !isUrl(input.value.trim())) {
            performSearch(input.value.trim(), false);
        }
    }

    if (btnBm25) btnBm25.addEventListener('click', (e) => { e.preventDefault(); setMode('bm25'); });
    if (btnAi) btnAi.addEventListener('click', (e) => { e.preventDefault(); setMode('ai'); });

    // Show toast
    function showToast(message, isError = true) {
        if (!toast) return;
        toast.textContent = message;
        toast.className = `absolute top-full mt-2 left-0 right-0 z-50 text-xs font-semibold px-3 py-2 rounded-lg border shadow-lg ${isError ? 'bg-red-50 text-red-600 border-red-200' : 'bg-green-50 text-green-600 border-green-200'}`;
        toast.classList.remove('hidden');
        setTimeout(() => toast.classList.add('hidden'), 5000);
    }

    // Input handler (Debounced live search dropdown)
    input.addEventListener('input', function(e) {
        clearTimeout(typingTimer);
        const text = input.value.trim();
        if (toast) toast.classList.add('hidden');
        
        if (!text) {
            if (dropdown) dropdown.classList.add('hidden');
            if (toggleContainer) toggleContainer.classList.add('hidden');
            if (icon) icon.textContent = '🔍';
            return;
        }

        if (isUrl(text)) {
            // URL Mode (Import)
            if (icon) icon.textContent = '🔗';
            if (toggleContainer) toggleContainer.classList.add('hidden');
            if (dropdown) dropdown.classList.add('hidden');
        } else {
            // Text Mode (Search)
            if (icon) icon.textContent = '🔎';
            if (toggleContainer) toggleContainer.classList.remove('hidden');
            typingTimer = setTimeout(() => performSearch(text, false), typingInterval);
        }
    });

    // Keydown Enter Handler (Immediate action on Enter key)
    input.addEventListener('keydown', function(e) {
        if (e.key === 'Enter') {
            e.preventDefault();
            clearTimeout(typingTimer);
            const text = input.value.trim();
            if (!text) return;

            if (isUrl(text)) {
                performImport(text);
            } else {
                // If results are already loaded in dropdown and dropdown is open, navigate to top result
                const firstResult = resultsList ? resultsList.querySelector('a') : null;
                if (firstResult && dropdown && !dropdown.classList.contains('hidden')) {
                    window.location.href = firstResult.href;
                } else {
                    // Otherwise execute search immediately and auto-navigate to best match
                    performSearch(text, true);
                }
            }
        }
    });

    // Search function with optional auto-navigate on Enter
    function performSearch(query, autoNavigate = false) {
        if (spinner) spinner.classList.remove('hidden');
        const endpoint = searchMode === 'bm25' ? '/readspace/api/search/keyword/' : '/readspace/api/search/semantic/';
        
        fetch(`${endpoint}?q=${encodeURIComponent(query)}`)
            .then(r => r.json())
            .then(data => {
                if (spinner) spinner.classList.add('hidden');
                if (data.status === 'success') {
                    if (autoNavigate && data.results && data.results.length > 0) {
                        window.location.href = `/readspace/${data.results[0].id}/`;
                    } else {
                        renderResults(data.results, query);
                    }
                } else {
                    showToast(data.message || 'Error searching', true);
                }
            })
            .catch(err => {
                if (spinner) spinner.classList.add('hidden');
                showToast('Network error while searching.', true);
            });
    }

    function renderResults(results, query) {
        if (!resultsList || !dropdown) return;
        resultsList.innerHTML = '';

        if (results.length === 0) {
            resultsList.innerHTML = `<div class="p-4 text-center text-sm text-slate-500">No articles found matching "${query}".</div>`;
        } else {
            results.forEach(res => {
                const a = document.createElement('a');
                a.href = `/readspace/${res.id}/`;
                a.className = 'block p-3 border-b border-slate-100 hover:bg-blue-50 transition group';
                
                const titleDiv = document.createElement('div');
                titleDiv.className = 'font-bold text-slate-800 text-sm mb-1 line-clamp-1 group-hover:text-blue-600';
                titleDiv.textContent = res.title;
                
                const metaDiv = document.createElement('div');
                metaDiv.className = 'flex items-center gap-2 text-xs text-slate-400 mb-1';
                
                let metaHtml = `<span class="bg-slate-100 text-slate-500 px-1.5 py-0.5 rounded uppercase font-bold text-[10px]">${res.source}</span>`;
                if (res.date) {
                    metaHtml += `<span>${res.date}</span>`;
                }
                if (res.similarity !== undefined) {
                    metaHtml += `<span class="text-indigo-500 font-semibold flex items-center gap-0.5"><svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>${res.similarity}%</span>`;
                }
                metaDiv.innerHTML = metaHtml;

                const snippetDiv = document.createElement('div');
                snippetDiv.className = 'text-xs text-slate-500 line-clamp-2';
                snippetDiv.textContent = res.snippet || '';
                
                a.appendChild(titleDiv);
                a.appendChild(metaDiv);
                if (res.snippet) a.appendChild(snippetDiv);
                resultsList.appendChild(a);
            });
        }
        dropdown.classList.remove('hidden');
    }

    // Import function
    function performImport(url) {
        input.disabled = true;
        if (spinner) spinner.classList.remove('hidden');
        if (dropdown) dropdown.classList.add('hidden');

        const csrfTokenEl = document.querySelector('[name=csrfmiddlewaretoken]');
        const csrfToken = csrfTokenEl ? csrfTokenEl.value : '';
        const formData = new URLSearchParams();
        formData.append('url', url);

        fetch("/readspace/import/", {
            method: 'POST',
            headers: {
                'X-Requested-With': 'XMLHttpRequest',
                'X-CSRFToken': csrfToken,
                'Content-Type': 'application/x-www-form-urlencoded'
            },
            body: formData
        })
        .then(response => response.json())
        .then(data => {
            if (data.status === 'started' || data.status === 'success') {
                window.location.href = `/readspace/${data.id}/`;
            } else {
                showToast(data.message || 'Error importing article', true);
                input.disabled = false;
                if (spinner) spinner.classList.add('hidden');
            }
        })
        .catch(err => {
            showToast('Network error. Please try again.', true);
            input.disabled = false;
            if (spinner) spinner.classList.add('hidden');
        });
    }

    // Close dropdown on click outside
    document.addEventListener('click', (e) => {
        if (omniContainer && !omniContainer.contains(e.target) && dropdown) {
            dropdown.classList.add('hidden');
        }
    });
});
