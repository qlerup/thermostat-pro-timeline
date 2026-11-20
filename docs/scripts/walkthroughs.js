// Plain Markdown links also work when these pages are read on GitHub.
document.querySelectorAll(".md-typeset a").forEach(link => {
  if (link.textContent !== "Play walkthrough") return;
  const preview = link.closest("p")?.previousElementSibling?.querySelector("a img");
  if (!preview) return;
  const still = preview.src;
  const animation = link.href;
  const button = document.createElement("button");
  button.type = "button";
  button.className = "walkthrough-toggle";
  button.textContent = link.textContent;
  button.setAttribute("aria-pressed", "false");
  button.setAttribute("aria-label", "Play walkthrough: " + preview.alt);
  button.addEventListener("click", () => {
    const play = button.getAttribute("aria-pressed") !== "true";
    preview.src = play ? animation : still;
    button.setAttribute("aria-pressed", String(play));
    button.textContent = play ? "Show still image" : "Play walkthrough";
    button.setAttribute("aria-label", button.textContent + ": " + preview.alt);
  });
  link.replaceWith(button);
});
