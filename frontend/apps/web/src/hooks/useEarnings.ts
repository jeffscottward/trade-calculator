import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useEffect, useCallback } from "react";
import { format } from "date-fns";

interface EarningsProgress {
	type: "progress" | "complete" | "error";
	current?: number;
	total?: number;
	ticker?: string;
	message?: string;
	data?: any[];
}

interface UseEarningsOptions {
	onProgress?: (progress: EarningsProgress) => void;
}

export function useEarningsQuery(date: Date, options?: UseEarningsOptions) {
	const [progress, setProgress] = useState<EarningsProgress | null>(null);
	const [isStreaming, setIsStreaming] = useState(false);
	const queryClient = useQueryClient();
	const dateStr = format(date, "yyyy-MM-dd");

	// Query key for React Query caching
	const queryKey = ["earnings", dateStr];

	// Custom fetcher that handles SSE
	const fetchEarnings = useCallback(async () => {
		// Check if we have cached data first
		const cachedData = queryClient.getQueryData(queryKey);
		if (cachedData) {
			return cachedData;
		}

		return new Promise((resolve, reject) => {
			const eventSource = new EventSource(
				`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/earnings/${dateStr}/stream`
			);

			setIsStreaming(true);
			let finalData: any[] = []; // Initialize as empty array instead of null

			eventSource.onmessage = (event) => {
				try {
					const data = JSON.parse(event.data);

					// Only update progress state for actual progress messages
					if (data.type === "progress") {
						setProgress(data);
					}

					// Call optional progress callback
					if (options?.onProgress) {
						options.onProgress(data);
					}

					// Handle different message types
					if (data.type === "complete") {
						finalData = data.earnings || [];
						eventSource.close();
						setIsStreaming(false);
						setProgress(null);
						resolve(finalData);
					} else if (data.type === "cached") {
						finalData = data.earnings || [];
						eventSource.close();
						setIsStreaming(false);
						setProgress(null);
						resolve(finalData);
					} else if (data.type === "error") {
						eventSource.close();
						setIsStreaming(false);
						setProgress(null);
						// Return empty array on error instead of rejecting
						resolve([]);
					} else if (data.type === "start" || data.type === "fetched") {
						// These are status messages, don't update progress bar
						// Silently ignore to prevent progress bar jumping
					}
				} catch (error) {
					// Silently handle parsing errors
				}
			};

			eventSource.onerror = (error) => {
				eventSource.close();
				setIsStreaming(false);
				setProgress(null);
				// Return empty array on error instead of rejecting
				resolve([]);
			};

			// Note: This cleanup return is not actually used by Promise
			// The cleanup would need to be handled differently
		});
	}, [dateStr, queryClient, queryKey, options]);

	// Use React Query for caching and state management
	const query = useQuery({
		queryKey,
		queryFn: fetchEarnings,
		staleTime: 1000 * 60 * 60, // Cache for 1 hour
		gcTime: 1000 * 60 * 60 * 24, // Keep in cache for 24 hours
		refetchOnWindowFocus: false,
		refetchOnMount: false,
		retry: 1,
	});

	return {
		...query,
		progress,
		isStreaming,
	};
}

// Helper hook for invalidating earnings cache
export function useInvalidateEarnings() {
	const queryClient = useQueryClient();

	return useCallback(
		(date?: Date) => {
			if (date) {
				const dateStr = format(date, "yyyy-MM-dd");
				queryClient.invalidateQueries({ queryKey: ["earnings", dateStr] });
			} else {
				// Invalidate all earnings queries
				queryClient.invalidateQueries({ queryKey: ["earnings"] });
			}
		},
		[queryClient]
	);
}

// Helper hook for prefetching earnings data
export function usePrefetchEarnings() {
	const queryClient = useQueryClient();

	return useCallback(
		async (date: Date) => {
			const dateStr = format(date, "yyyy-MM-dd");
			await queryClient.prefetchQuery({
				queryKey: ["earnings", dateStr],
				queryFn: async () => {
					// Simple fetch for prefetching (no SSE needed)
					const response = await fetch(
						`${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/api/earnings/${dateStr}`
					);
					if (!response.ok) {
						throw new Error("Failed to prefetch earnings");
					}
					return response.json();
				},
				staleTime: 1000 * 60 * 60, // Cache for 1 hour
			});
		},
		[queryClient]
	);
}