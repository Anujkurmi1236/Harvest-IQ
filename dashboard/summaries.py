"""Farmer-friendly explanations of structured Harvest-IQ model results."""


HINDI = "हिन्दी"


def _is_hindi(language: str) -> bool:
    return language == HINDI


def summarize_yield(item: str, result: dict, language: str) -> str:
    if not result.get("ok"):
        return (
            f"Yield prediction is unavailable: {result.get('error', 'unknown error')}."
            if not _is_hindi(language)
            else f"उपज का अनुमान उपलब्ध नहीं है: {result.get('error', 'अज्ञात त्रुटि')}।"
        )

    predicted = result.get("predicted_yield_kg_ha", 0)
    low = result.get("low_kg_ha", 0)
    high = result.get("high_kg_ha", 0)
    confidence = (
        "Confidence is lower because this crop had limited test data."
        if result.get("low_confidence")
        else "The model has a typical level of confidence for this crop."
    )
    confidence_hi = (
        "इस फसल के लिए परीक्षण डेटा कम होने के कारण अनुमान का भरोसा कम है।"
        if result.get("low_confidence")
        else "इस फसल के लिए मॉडल का भरोसा सामान्य स्तर का है।"
    )
    if _is_hindi(language):
        return (
            f"{item} की अनुमानित उपज {predicted:,.0f} किलोग्राम प्रति हेक्टेयर है। "
            f"संभावित सीमा {low:,.0f} से {high:,.0f} किलोग्राम प्रति हेक्टेयर है। "
            f"{confidence_hi}"
        )
    return (
        f"The expected yield for {item} is {predicted:,.0f} kg per hectare. "
        f"The likely range is {low:,.0f}–{high:,.0f} kg per hectare. "
        f"{confidence}"
    )


def summarize_weather(result: dict, language: str) -> str:
    if not result.get("ok"):
        return (
            f"Weather analysis is unavailable: {result.get('error', 'unknown error')}."
            if not _is_hindi(language)
            else f"मौसम का विश्लेषण उपलब्ध नहीं है: {result.get('error', 'अज्ञात त्रुटि')}।"
        )

    stress = float(result.get("environmental_stress_index", 0))
    if stress < 33:
        level_en, level_hi = "low", "कम"
    elif stress < 67:
        level_en, level_hi = "moderate", "मध्यम"
    else:
        level_en, level_hi = "high", "अधिक"

    if _is_hindi(language):
        return (
            f"मौसम से संबंधित तनाव का स्तर {level_hi} है ({stress:.1f}/100)। "
            "अधिक स्कोर का अर्थ है कि फसल पर मौसम का दबाव अधिक हो सकता है। "
            "सिंचाई, तापमान और स्थानीय मौसम की निगरानी करें।"
        )
    return (
        f"The environmental stress level is {level_en} ({stress:.1f}/100). "
        "A higher score means weather may put more pressure on the crop. "
        "Monitor irrigation, temperature, and local weather conditions."
    )


def summarize_market(result: dict, language: str) -> str:
    if not result.get("ok"):
        return (
            f"Market analysis is unavailable: {result.get('error', 'unknown error')}."
            if not _is_hindi(language)
            else f"बाजार का विश्लेषण उपलब्ध नहीं है: {result.get('error', 'अज्ञात त्रुटि')}।"
        )

    level = result.get("predicted_index_level", 0)
    if result.get("is_historical"):
        if _is_hindi(language):
            return (
                f"इस वर्ष के लिए उपलब्ध ऐतिहासिक मूल्य सूचकांक {level:.1f} है। "
                "यह रुपये में कीमत नहीं है, बल्कि बाजार के स्तर का संकेत है।"
            )
        return (
            f"The available historical price index for this year is {level:.1f}. "
            "This is not a rupee price; it indicates the relative market level."
        )

    last_level = result.get("last_known_index_level", 0)
    direction_hi = "बढ़ने" if level >= last_level else "घटने"
    direction_en = "increase" if level >= last_level else "decrease"
    if _is_hindi(language):
        return (
            f"अनुमानित मूल्य सूचकांक {level:.1f} है, जबकि अंतिम उपलब्ध स्तर "
            f"{last_level:.1f} था। इससे बाजार में {direction_hi} का संकेत मिलता है। "
            "यह सूचकांक 2014–2016 = 100 पर आधारित है और रुपये में कीमत नहीं बताता।"
        )
    return (
        f"The predicted price index is {level:.1f}, compared with the last known "
        f"level of {last_level:.1f}. This suggests a possible {direction_en} in "
        "the relative market level. The index uses 2014–2016 = 100 and is not a rupee price."
    )


def summarize_supply_chain(result: dict, language: str) -> str:
    if not result.get("ok"):
        return (
            f"Supply-chain analysis is unavailable: {result.get('error', 'unknown error')}."
            if not _is_hindi(language)
            else f"आपूर्ति श्रृंखला का विश्लेषण उपलब्ध नहीं है: {result.get('error', 'अज्ञात त्रुटि')}।"
        )

    recommendation = result.get("recommendation", "unknown")
    profit = float(result.get("net_profit", 0))
    label_en = "sell now" if recommendation == "sell_now" else recommendation.replace("_", " ")
    label_hi = "अभी बेचें" if recommendation == "sell_now" else recommendation.replace("_", " ")
    if _is_hindi(language):
        return (
            f"मॉडल के अनुसार {label_hi} विकल्प बेहतर दिखता है। अनुमानित शुद्ध लाभ "
            f"₹{profit:,.0f} है। भंडारण लागत, परिवहन खर्च और फसल के संभावित नुकसान "
            "को ध्यान में रखकर यह सुझाव दिया गया है।"
        )
    return (
        f"The model indicates that “{label_en}” may be the better option. "
        f"The estimated net profit is ₹{profit:,.0f}. This recommendation considers "
        "storage cost, transport cost, and possible crop loss."
    )


def summarize_overall(
    item: str,
    yield_result: dict,
    weather_result: dict,
    market_result: dict,
    supply_chain_result: dict,
    language: str,
) -> str:
    if _is_hindi(language):
        return (
            f"{item} के लिए यह अनुमानित विश्लेषण है, गारंटी नहीं। उपज, मौसम का तनाव, "
            "बाजार का सूचकांक और बेचने या भंडारण के विकल्प को साथ देखकर निर्णय लें। "
            "स्थानीय मौसम, मिट्टी, मंडी भाव और अपनी खेती की स्थिति से इस सुझाव की पुष्टि करें।"
        )
    return (
        f"This is an estimate for {item}, not a guarantee. Consider the yield, weather "
        "stress, market index, and sell-or-store options together. Confirm the result "
        "with local weather, soil conditions, mandi prices, and your farm situation."
    )
