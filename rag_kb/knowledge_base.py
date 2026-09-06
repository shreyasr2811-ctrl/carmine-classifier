"""
Small curated knowledge base of general, factual information about
Invasive Ductal Carcinoma (IDC) and breast histopathology, used to ground
the LLM's plain-language explanation of a model prediction via RAG.

This is general educational content, not medical advice. Every generated
explanation should carry a disclaimer directing the user to a qualified
pathologist/oncologist for actual diagnosis.
"""

DOCUMENTS = [
    {
        "id": "idc_overview",
        "text": (
            "Invasive Ductal Carcinoma (IDC) is the most common type of breast cancer, "
            "accounting for roughly 70-80% of all breast cancer diagnoses. It begins in "
            "the milk ducts of the breast and invades surrounding breast tissue. On "
            "histopathology slides, IDC regions typically show irregular clusters of "
            "malignant epithelial cells, increased nuclear density, pleomorphic "
            "(variably shaped/sized) nuclei, and disrupted normal duct architecture."
        ),
    },
    {
        "id": "benign_tissue",
        "text": (
            "Benign (non-IDC) breast tissue on histopathology slides generally shows "
            "organized, regular glandular or ductal structures, uniform cell nuclei, "
            "and preserved tissue architecture. Fibrous stroma, fat cells (adipocytes), "
            "and normal duct/lobule patterns are common in benign regions."
        ),
    },
    {
        "id": "whole_slide_imaging",
        "text": (
            "Whole Slide Imaging (WSI) is the process of digitizing entire glass "
            "microscope slides at high resolution, allowing pathologists and computer "
            "algorithms to analyze tissue at a cellular level. Because WSI files are "
            "extremely large (often gigapixel images), automated analysis typically "
            "works on small image patches (e.g., 50x50 pixels) extracted from the "
            "slide, and results are aggregated across the many patches from one slide."
        ),
    },
    {
        "id": "patch_based_classification",
        "text": (
            "Patch-based classification models predict a label (e.g., benign vs. IDC) "
            "for small tissue patches rather than an entire slide. A single patch "
            "prediction reflects only what is visible in that small region and does "
            "not by itself represent a diagnosis for the whole tissue sample or "
            "patient. A full clinical assessment considers many patches, slide-level "
            "context, clinical history, and additional tests."
        ),
    },
    {
        "id": "grading_and_staging",
        "text": (
            "Breast cancer severity is formally described using tumor grade (how "
            "abnormal cells look and how quickly they are likely to grow) and stage "
            "(how far the cancer has spread, based on tumor size, lymph node "
            "involvement, and metastasis). Neither grade nor stage can be determined "
            "from a single image patch; they require full pathological review, "
            "imaging, and sometimes additional lab tests (e.g., hormone receptor "
            "status, HER2 status)."
        ),
    },
    {
        "id": "risk_factors",
        "text": (
            "Common risk factors associated with breast cancer include age, family "
            "history and inherited gene mutations (e.g., BRCA1/BRCA2), dense breast "
            "tissue, prior radiation exposure, hormone replacement therapy, obesity, "
            "and alcohol consumption. Having risk factors does not mean a person will "
            "develop cancer, and their absence does not rule it out."
        ),
    },
    {
        "id": "screening_and_next_steps",
        "text": (
            "Screening tools such as mammography, ultrasound, and MRI are used to "
            "detect suspicious areas in breast tissue, which may then be biopsied for "
            "histopathological examination. If a biopsy or imaging result raises "
            "concern, the appropriate next step is always consultation with a "
            "qualified oncologist, radiologist, or pathologist, who can order "
            "confirmatory tests and provide a full clinical diagnosis and treatment "
            "plan."
        ),
    },
    {
        "id": "ai_limitations",
        "text": (
            "AI/machine learning models for histopathology image classification are "
            "trained on limited datasets and can make mistakes, including false "
            "positives (flagging benign tissue as malignant) and false negatives "
            "(missing malignant tissue). Such models are research/educational tools "
            "and are not approved substitutes for diagnosis by a licensed medical "
            "professional. Model confidence scores reflect statistical certainty "
            "based on training data patterns, not clinical certainty."
        ),
    },
    {
        "id": "staining_he",
        "text": (
            "Most histopathology slides, including those in common breast cancer "
            "datasets, use Hematoxylin and Eosin (H&E) staining. Hematoxylin stains "
            "cell nuclei a dark blue/purple color, while eosin stains the "
            "cytoplasm and extracellular matrix pink. Pathologists and image "
            "classification models use these color and texture differences, along "
            "with nuclear shape and tissue structure, to distinguish tissue types."
        ),
    },
    {
        "id": "false_positive_negative",
        "text": (
            "In a diagnostic context, a false positive means the model predicts "
            "cancer (malignant) when the tissue is actually benign, which can cause "
            "unnecessary worry or follow-up testing. A false negative means the "
            "model predicts benign when the tissue is actually malignant, which is "
            "generally considered more clinically dangerous because it could delay "
            "treatment. This is why automated predictions should always be confirmed "
            "by a qualified professional rather than acted on alone."
        ),
    },
]
