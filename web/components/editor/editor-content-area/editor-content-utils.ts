export function getEditorContentMaxWidth(isLeftExpanded: boolean, isRightExpanded: boolean) {
  if (isLeftExpanded && isRightExpanded) {
    return "max-w-[600px]";
  }

  if (isLeftExpanded || isRightExpanded) {
    return "max-w-[680px]";
  }

  return "max-w-[720px]";
}
