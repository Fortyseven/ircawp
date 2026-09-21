import { mount } from "svelte";
import "@fontsource/roboto-condensed/400.css";
import "@fontsource/roboto-condensed/500.css";
import "@fontsource/roboto-condensed/800.css";
import App from "./App.svelte";
import "./style.css";

const app = mount(App, {
    target: document.getElementById("app"),
});

export default app;
