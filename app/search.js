// search.html's script: lists each published Post and Page in search-index.json
// (written by `cms publish`) whose title or excerpt holds every typed word.
// Plain JavaScript, no library; every URL is relative, for a Pages subfolder.
(function () {
  var input = document.getElementById("search-input");
  var status = document.getElementById("search-status");
  var results = document.getElementById("search-results");
  var index = null;  // the index's items, once it has loaded
  var failed = false;

  // Titles and excerpts are user content: build nodes with textContent,
  // never innerHTML.
  function resultRow(item) {
    var link = document.createElement("a");
    link.className = "post-card";
    link.href = item.url;
    var title = document.createElement("span");
    title.className = "post-card__title";
    title.textContent = item.title;
    var excerpt = document.createElement("span");
    excerpt.className = "post-card__excerpt";
    excerpt.textContent = item.excerpt;
    link.append(title, excerpt);
    var row = document.createElement("li");
    row.append(link);
    return row;
  }

  function showResults() {
    if (failed) { return; }  // keep the "unavailable" message up
    var words = input.value.toLowerCase().split(/\s+/).filter(Boolean);
    results.replaceChildren();
    status.textContent = words.length && index === null ? "Loading the search index…" : "";
    if (index === null) { return; }
    // Keep the words in the address (?q=…), so Back from a result keeps them.
    history.replaceState(null, "", words.length ? "?q=" + encodeURIComponent(input.value) : "search.html");
    if (words.length === 0) { return; }
    var hits = index.filter(function (item) {
      var text = (item.title + " " + item.excerpt).toLowerCase();
      return words.every(function (word) { return text.indexOf(word) !== -1; });
    });
    results.append.apply(results, hits.map(resultRow));
    status.textContent = hits.length === 1 ? "1 result" :
      hits.length === 0 ? "No results" : hits.length + " results";
  }

  input.value = new URLSearchParams(location.search).get("q") || "";
  input.addEventListener("input", showResults);
  fetch("search-index.json")
    .then(function (response) {
      if (!response.ok) { throw new Error("search index " + response.status); }
      return response.json();
    })
    .then(function (items) { index = items; showResults(); })
    .catch(function () {
      failed = true;
      status.textContent = "Search is unavailable: the search index didn't load.";
    });
})();
