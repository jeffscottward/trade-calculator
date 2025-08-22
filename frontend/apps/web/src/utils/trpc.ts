import { QueryCache, QueryClient } from "@tanstack/react-query";
import { createTRPCClient, httpBatchLink } from "@trpc/client";
import { createTRPCOptionsProxy } from "@trpc/tanstack-react-query";
import { toast } from "sonner";
import type { AppRouter } from "../../../server/src/routers";

export const queryClient = new QueryClient({
	queryCache: new QueryCache({
		onError: (error) => {
			// Don't show toast for authentication errors
			const isAuthError = error.message?.toLowerCase().includes('unauthorized') || 
				error.message?.toLowerCase().includes('not authenticated') ||
				error.message?.toLowerCase().includes('unauthenticated');
			
			if (!isAuthError) {
				toast.error(error.message, {
					action: {
						label: "retry",
						onClick: () => {
							queryClient.invalidateQueries();
						},
					},
				});
			}
		},
	}),
});

const trpcClient = createTRPCClient<AppRouter>({
	links: [
		httpBatchLink({
			url: `${process.env.NEXT_PUBLIC_SERVER_URL}/trpc`,
			fetch(url, options) {
				return fetch(url, {
					...options,
					credentials: "include",
				});
			},
		}),
	],
});

export const trpc = createTRPCOptionsProxy<AppRouter>({
	client: trpcClient,
	queryClient,
});
