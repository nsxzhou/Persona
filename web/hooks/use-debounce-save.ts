import { useCallback, useEffect, useRef } from "react";

export function useDebounceSave<T extends string, V = string>(
  onSave: (field: T, value: V) => void | Promise<void>,
  delay = 1000
) {
  const saveTimers = useRef<Record<string, NodeJS.Timeout>>({});
  const onSaveRef = useRef(onSave);

  useEffect(() => {
    onSaveRef.current = onSave;
  }, [onSave]);

  const debouncedSave = useCallback(
    (field: T, value: V) => {
      const key = String(field);
      if (saveTimers.current[key]) {
        clearTimeout(saveTimers.current[key]);
      }
      saveTimers.current[key] = setTimeout(() => {
        void onSaveRef.current(field, value);
      }, delay);
    },
    [delay]
  );

  useEffect(() => {
    const timers = saveTimers.current;
    return () => {
      Object.values(timers).forEach(clearTimeout);
    };
  }, []);

  return debouncedSave;
}
