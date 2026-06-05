// File: js/string_concat.js

import { app } from "../../scripts/app.js";
import { setupDynamicInputs } from "./dynamic_utils.js";

app.registerExtension({
    name: "FlowControl.StringConcat",
    async beforeRegisterNodeDef(nodeType, nodeData, app) {
        if (nodeData.name === "FlowControl_StringConcat") {

            setupDynamicInputs(nodeType, {
                prefix: "text_",
                inputType: "*"
            });

        }
    },
});