/**
 * Shared customer autocomplete (name + number + optional email, and optional job location fields).
 * Initialized from templates via initKTCustomerAutocomplete({ ... }).
 */
(function () {
    'use strict';

    function debounce(func, delay) {
        let timer;
        return function () {
            const ctx = this;
            const args = arguments;
            clearTimeout(timer);
            timer = setTimeout(function () {
                func.apply(ctx, args);
            }, delay);
        };
    }

    function positionBox(input, box) {
        box.style.width = input.offsetWidth + 'px';
        box.style.left = input.offsetLeft + 'px';
        box.style.top = input.offsetTop + input.offsetHeight + 'px';
    }

    function buildUrl(apiUrl, field, term) {
        const base = apiUrl.replace(/\/?$/, '');
        return base + '/?field=' + encodeURIComponent(field) + '&term=' + encodeURIComponent(term);
    }

    /**
     * @param {Object} cfg
     * @param {string} cfg.apiUrl - resolved URL path for the suggestions endpoint (no query string)
     * @param {string} cfg.nameInputSelector
     * @param {string} cfg.nameListId
     * @param {string} [cfg.numberInputSelector]
     * @param {string} [cfg.numberListId]
     * @param {string} [cfg.emailInputSelector]
     * @param {number} [cfg.minNameChars=3]
     * @param {number} [cfg.minNumberChars=5]
     * @param {Array<{inputSelector:string,listId:string,field:string,minChars?:number}>} [cfg.extraStringFields]
     */
    window.initKTCustomerAutocomplete = function (cfg) {
        const apiUrl = cfg.apiUrl;
        const nameInput = document.querySelector(cfg.nameInputSelector);
        const nameBox = document.getElementById(cfg.nameListId);
        const numInput = cfg.numberInputSelector
            ? document.querySelector(cfg.numberInputSelector)
            : null;
        const numBox = cfg.numberListId ? document.getElementById(cfg.numberListId) : null;
        const emailInput = cfg.emailInputSelector
            ? document.querySelector(cfg.emailInputSelector)
            : null;
        const minName = cfg.minNameChars != null ? cfg.minNameChars : 3;
        const minNum = cfg.minNumberChars != null ? cfg.minNumberChars : 5;

        if (!nameInput || !nameBox || !apiUrl) {
            return;
        }

        function fetchSuggest(field, term) {
            return fetch(buildUrl(apiUrl, field, term)).then(function (r) {
                return r.json();
            });
        }

        const handleName = debounce(function () {
            const q = nameInput.value;
            if (q.length < minName) {
                nameBox.style.display = 'none';
                return;
            }
            fetchSuggest('name', q).then(function (data) {
                nameBox.innerHTML = '';
                if (!data || !data.length) {
                    nameBox.style.display = 'none';
                    return;
                }
                data.forEach(function (item) {
                    const li = document.createElement('li');
                    if (typeof item === 'object' && item.name !== undefined) {
                        li.textContent = item.name;
                        li.style.cursor = 'pointer';
                        li.style.padding = '5px';
                        li.addEventListener('click', function () {
                            nameInput.value = item.name;
                            if (numInput && item.number) {
                                numInput.value = item.number;
                            }
                            if (emailInput && item.email) {
                                emailInput.value = item.email;
                            }
                            nameBox.style.display = 'none';
                        });
                    }
                    nameBox.appendChild(li);
                });
                nameBox.style.display = 'block';
                positionBox(nameInput, nameBox);
            });
        }, 300);

        nameInput.addEventListener('input', handleName);
        document.addEventListener('click', function (e) {
            if (!nameInput.contains(e.target) && !nameBox.contains(e.target)) {
                nameBox.style.display = 'none';
            }
        });

        if (numInput && numBox) {
            const handleNum = debounce(function () {
                const q = numInput.value;
                if (q.length < minNum) {
                    numBox.style.display = 'none';
                    return;
                }
                fetchSuggest('number', q).then(function (data) {
                    numBox.innerHTML = '';
                    if (!data || !data.length) {
                        numBox.style.display = 'none';
                        return;
                    }
                    data.forEach(function (item) {
                        const li = document.createElement('li');
                        li.textContent = item;
                        li.style.cursor = 'pointer';
                        li.style.padding = '5px';
                        li.addEventListener('click', function () {
                            numInput.value = item;
                            numBox.style.display = 'none';
                        });
                        numBox.appendChild(li);
                    });
                    numBox.style.display = 'block';
                    positionBox(numInput, numBox);
                });
            }, 300);

            numInput.addEventListener('input', handleNum);
            document.addEventListener('click', function (e) {
                if (!numInput.contains(e.target) && !numBox.contains(e.target)) {
                    numBox.style.display = 'none';
                }
            });
        }

        (cfg.extraStringFields || []).forEach(function (ef) {
            const inp = document.querySelector(ef.inputSelector);
            const box = document.getElementById(ef.listId);
            if (!inp || !box) {
                return;
            }
            const minC = ef.minChars != null ? ef.minChars : 3;
            const handle = debounce(function () {
                const q = inp.value;
                if (q.length < minC) {
                    box.style.display = 'none';
                    return;
                }
                fetchSuggest(ef.field, q).then(function (data) {
                    box.innerHTML = '';
                    if (!data || !data.length) {
                        box.style.display = 'none';
                        return;
                    }
                    data.forEach(function (item) {
                        const li = document.createElement('li');
                        li.textContent = item;
                        li.style.cursor = 'pointer';
                        li.style.padding = '5px';
                        li.addEventListener('click', function () {
                            inp.value = item;
                            box.style.display = 'none';
                        });
                        box.appendChild(li);
                    });
                    box.style.display = 'block';
                    positionBox(inp, box);
                });
            }, 300);
            inp.addEventListener('input', handle);
            document.addEventListener('click', function (e) {
                if (!inp.contains(e.target) && !box.contains(e.target)) {
                    box.style.display = 'none';
                }
            });
        });
    };
})();
