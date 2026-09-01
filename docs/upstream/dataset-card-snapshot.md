---
license: apache-2.0
pretty_name: Egocentric-10K Evaluation Dataset
---

<div style="margin: 20px 0;">
  <table style="border-collapse: collapse; width: 100%;">
    <tr>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/SHyQth6VqSqbAOf_47Swp.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/ba_6c35-M_qrzjXe1aYOf.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/O2JIcQw7eEcqlngCXsWWV.png" style="width: 100%; max-width: 100%;"/></td>
    </tr>
    <tr>
      <td style="text-align: center; padding: 5px;"><strong>Egocentric10K</strong></td>
      <td style="text-align: center; padding: 5px;"><strong>Ego4D</strong></td>
      <td style="text-align: center; padding: 5px;"><strong>Epic-Kitchens</strong></td>
    </tr>
  </table>
</div>

<p style="margin: 20px 0; line-height: 1.6;">
To evaluate the three in-the-wild egocentric datasets Egocentric-10K, Ego4D, and EPIC-KITCHENS-100 on hand visibility and active manipulation density as a proxy for data efficiency, we randomly sample 10k frames from each dataset and run them through a gemini-2.5-flash.
</p>

## Hand Visibility

<div style="border: 1px solid #d0d7de; border-radius: 6px; padding: 15px; margin: 15px 0;">
  <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6;">
    <strong>Prompt:</strong><br/>
    You are labeling an egocentric first-person image. Your task is to count how many camera-wearer's hands are visually present in the image: 0, 1, or 2.<br/><br/>
    <strong>Rules:</strong><br/>
    • Only count hands that are directly visible.<br/>
    • Do not infer hands that are outside the frame or potentially behind objects.<br/>
    • Ignore hands belonging to other people.<br/>
    • Any amount of visibility counts (even fingertips).<br/>
    • Return only one of: 0, 1, 2. No extra words.
  </p>
  <p style="margin: 10px 0 5px 0; font-size: 14px;"><strong>Response Schema:</strong></p>
  <pre style="padding: 10px; border-radius: 4px; margin: 0; overflow-x: auto;"><code>{
  "type": "OBJECT",
  "properties": {
    "hand_count": {
      "type": "INTEGER"
    }
  },
  "required": ["hand_count"]
}</code></pre>
</div>

<div style="width: 100%; overflow-x: auto;">

| Dataset | Frames | 0 Hands | 1+ Hands | 2 Hands |
|---------|--------|---------|----------|---------|
| **Egocentric-10K** | 10,000 | **3.58%** | **96.42%** | **76.34%** |
| **Ego4D** | 10,000 | 32.67% | 67.33% | 36.95% |
| **EPIC-KITCHENS** | 10,000 | 9.63% | 90.37% | 61.05% |

</div>

<div style="margin: 20px 0;">
  <table style="border-collapse: collapse; width: 100%;">
    <tr>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/7hjr5j56RJG6D5bX4DroF.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/JucJX20yGU8PALGPbKzzZ.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/-oRVJBnoyKJxW9KIRY6ed.png" style="width: 100%; max-width: 100%;"/></td>
    </tr>
    <tr>
      <td style="text-align: center; padding: 5px;"><strong>Egocentric10K</strong><br/>2 hands</td>
      <td style="text-align: center; padding: 5px;"><strong>Ego4D</strong><br/>1 hand</td>
      <td style="text-align: center; padding: 5px;"><strong>Epic-Kitchens</strong><br/>2 hands</td>
    </tr>
  </table>
</div>

## Active Manipulation

<div style="border: 1px solid #d0d7de; border-radius: 6px; padding: 15px; margin: 15px 0;">
  <p style="margin: 0 0 10px 0; font-size: 14px; line-height: 1.6;">
    <strong>Prompt:</strong><br/>
    You are labeling an egocentric first-person image. Your task is to determine whether the camera-wearer is actively manipulating an object at this exact moment.<br/><br/>
    <strong>Definition:</strong><br/>
    "Active Manpulation" means the wearer is visibly using their hands to work on, modify, assemble, process, or handle physical objects, materials, components in pursuit of a specific goal<br/><br/>
    <strong>Rules:</strong><br/>
    • Do not infer actions that are not visible in the frame.<br/>
    • If the action is ambiguous or not clearly happening, respond "no."<br/>
    • Ignore objects held by other people.<br/>
    • Respond only with: "yes" or "no."
  </p>
  <p style="margin: 10px 0 5px 0; font-size: 14px;"><strong>Response Schema:</strong></p>
  <pre style="padding: 10px; border-radius: 4px; margin: 0; overflow-x: auto;"><code>{
  "type": "OBJECT",
  "properties": {
    "answer": {
      "type": "STRING",
      "enum": ["yes", "no"]
    }
  },
  "required": ["answer"]
}</code></pre>
</div>

<div style="width: 100%; overflow-x: auto;">

| Dataset | Frames | Active Labor |
|---------|--------|--------------|
| **Egocentric-10K** | 10,000 | **91.66%** |
| **Ego4D** | 10,000 | 50.07% |
| **EPIC-KITCHENS** | 10,000 | 85.04% |

</div>

<div style="margin: 20px 0;">
  <table style="border-collapse: collapse; width: 100%;">
    <tr>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/oPDy1unv--pv45acYePL8.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/uJYe6p8aM-rrM2nk-KoAY.png" style="width: 100%; max-width: 100%;"/></td>
      <td style="text-align: center; padding: 10px; width: 33.33%;"><img src="https://cdn-uploads.huggingface.co/production/uploads/690d75303df78b892c337cd4/q2G_-CGnSxHyYDrwacq_l.png" style="width: 100%; max-width: 100%;"/></td>
    </tr>
    <tr>
      <td style="text-align: center; padding: 5px;"><strong>Egocentric10K</strong><br/>Active Labor: Yes</td>
      <td style="text-align: center; padding: 5px;"><strong>Ego4D</strong><br/>Active Labor: No</td>
      <td style="text-align: center; padding: 5px;"><strong>Epic-Kitchens</strong><br/>Active Labor: Yes</td>
    </tr>
  </table>
</div>