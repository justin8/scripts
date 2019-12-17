/**
    Ugly hack to prevent the dashboard from opening up a new popup for the IDE.
**/

document.addEventListener("click", (evt) => {
    let parent = evt.target.parentNode;

    if (parent.tagName != "A")
        return;

    if (!/cloud9\/ide/.test(parent.href))
        return;

    evt.preventDefault();
    document.location.href = evt.target.parentNode.href;
});
