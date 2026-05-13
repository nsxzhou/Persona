export function getEditorContentMaxWidth(isLeftExpanded: boolean, isRightExpanded: boolean) {
  if (isLeftExpanded && isRightExpanded) {
    return "max-w-[820px]";
  }

  if (isLeftExpanded || isRightExpanded) {
    return "max-w-[960px]";
  }

  return "max-w-[1080px]";
}
