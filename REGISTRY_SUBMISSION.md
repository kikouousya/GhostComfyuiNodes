# Register In ComfyUI Custom Node Directory

This project can be listed in ComfyUI-Manager's node directory by submitting a PR to:

- `https://github.com/ltdrdata/ComfyUI-Manager`
- file: `custom-node-list.json`

## 1) JSON Entry

Use the content in `registry_entry.json` as the new item under `custom_nodes`.

## 2) Manual Web PR Steps

1. Open: `https://github.com/ltdrdata/ComfyUI-Manager/blob/main/custom-node-list.json`
2. Click the edit icon (fork if prompted).
3. Append the object from `registry_entry.json` to the `custom_nodes` array.
4. Create a pull request with title:

   `Add GhostComfyuiNodes to custom-node-list`

5. Recommended PR body:

   ```text
   Add GhostComfyuiNodes to ComfyUI-Manager custom-node-list.

   Repo:
   - https://github.com/kikouousya/GhostComfyuiNodes

   Notes:
   - install_type: git-clone
   - includes Python backend nodes and JS frontend helpers
   ```

## 3) Important Notes

- Keep `reference` and `files` as stable public GitHub URLs.
- Use English description for better discoverability.
- Review maintainers may adjust title/id format to match conventions.
