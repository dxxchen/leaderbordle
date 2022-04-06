import json
import supabase

from abc import ABC, abstractmethod


class VariantStats:
    def __init__(self, attempts=0, successes=0, guess_distribution=None, total_time_secs=0):
        self.attempts = attempts
        self.successes = successes
        self.guess_distribution = guess_distribution if guess_distribution is not None else {}
        self.total_time_secs = total_time_secs


class _Store:
    @abstractmethod
    def record_result(self, variant, user_id, result):
        pass

    @abstractmethod
    def read_leaders(self, days, variants):
        pass

    @abstractmethod
    def read_variant_stats(self, user_ids, variant):
        pass

    @abstractmethod
    def read_user_stats(self, user_id):
        pass


class InMemoryStore(_Store):
    def __init__(self, variants):
        # results is a dict of dict of array {variant: {user_id: [results]}}
        self.results = {}
        for variant in variants:
            self.results[variant.name()] = {}

    def record_result(self, variant, user_id, result):
        # This does not deduplicate results for the same iteration.
        if variant not in self.results:
            return

        self.results[variant].setdefault(user_id, []).append(result)

    def read_leaders(self, days, variants):
        pass

    def read_variant_stats(self, user_ids, variant):
        pass

    def read_user_stats(self, user_id):
        user_results = {}
        for variant_name, variant_results in self.results.items():
            if user_id not in variant_results:
                continue

            user_results[variant_name] = variant_results[user_id]

        all_stats = {}
        for variant_name, variant_results in user_results.items():
            stats = VariantStats()
            stats.attempts = len(variant_results)
            stats.successes = len([r for r in variant_results if r.success])

            unsorted_distribution = {}
            for result in variant_results:
                unsorted_distribution[result.guesses] = unsorted_distribution.setdefault(result.guesses, 0) + 1

            stats.guess_distribution = dict(sorted(unsorted_distribution.items()))

            all_stats[variant_name] = stats

        return all_stats


class SupabaseStore(_Store):
    def __init__(self, url, key):
        self.client = supabase.create_client(url, key)

    def record_result(self, variant, user_id, result):
        r = self.client.table("Attempts").upsert({
            'variant': variant,
            'user_id': user_id,
            'iteration': result.iteration,
            'guesses': result.guesses,
            'success': result.success,
            'time_secs': result.time_secs,
            'difficulty': result.difficulty
            }).execute()

    def read_leaders(self, days, variants):
        response = self.client.rpc('leaders', {'days': days, 'variants': variants})
        if response.status_code != 200:
            return None

        all_leaders = {}
        for row in response.json():
            variant_leaders = all_leaders.setdefault(row['variant'], {})
            variant_leaders[row['user_id']] = {
                'successes': row['successes'],
                'avg_guesses': row['avg_guesses']
            }

        for variant in all_leaders:
            all_leaders[variant] = dict(sorted(
                all_leaders[variant].items(),
                # Sort by the number of successes descending, then average guesses ascending.
                key=lambda kv: kv[1]['successes'] * 1000000 + (100000 - kv[1]['avg_guesses']),
                reverse=True))

        return all_leaders

    def read_variant_stats(self, user_ids, variant):
        pass

    def read_user_stats(self, user_id):
        response = self.client.rpc('read_user_stats', {'uid': user_id})
        if response.status_code != 200:
            return None

        all_stats = {}
        for row in response.json():
            stats = all_stats.setdefault(row['variant'], VariantStats())
            stats.attempts += row['total']
            if row['success']:
                stats.successes += row['total']
            stats.guess_distribution[row['guesses']] = stats.guess_distribution.setdefault(row['guesses'], 0) + row['total']
            if row['time_secs']:
                stats.total_time_secs += row['time_secs']

        for stats in all_stats.values():
            stats.guess_distribution = dict(sorted(stats.guess_distribution.items()))

        return all_stats