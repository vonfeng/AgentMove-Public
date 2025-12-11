"""Personal Memory module for AgentMove.

This module manages user mobility patterns through:
- Long-term memory: Historical activity patterns
- Short-term memory: Recent context stays
- User profile: Generated behavior insights
"""

from __future__ import annotations

from typing import Any

import pandas as pd


class Memory:
    """Memory unit for storing and processing user mobility patterns.
    
    Attributes:
        long_term_memory: Historical mobility pattern statistics.
        short_term_memory: Recent context visit information.
        user_profile: Generated textual user profile.
        memory_str_len: Maximum string length for memory prompt.
        memory_lens: Number of historical stays to consider.
    """
    
    # Constants for user profile generation
    EVENING_HOURS: frozenset[str] = frozenset({'5 PM', '6 PM', '8 PM'})
    REGULAR_HOURS: frozenset[str] = frozenset({'8 AM', '9 AM', '5 PM', '6 PM'})
    NIGHTLIFE_HOURS: frozenset[str] = frozenset({'10 PM', '11 PM', '12 AM', '1 AM', '2 AM'})
    COMMUTER_VENUES: frozenset[str] = frozenset({'Bus Station', 'Train Station'})
    LEISURE_VENUES: frozenset[str] = frozenset({'Beach', 'Park', 'Cafe', 'Food & Drink Shop', 'Restaurant'})
    SHOPPING_VENUES: frozenset[str] = frozenset({'Department Store', 'Clothing Store', 'Cosmetics Shop'})
    HEALTH_VENUES: frozenset[str] = frozenset({'Gym / Fitness Center'})
    FOOD_VENUES: frozenset[str] = frozenset({'Burger Joint', 'Thai Restaurant', 'Coffee Shop', 'Food & Drink Shop'})

    def __init__(
        self,
        know_stays: list[list[Any]],
        context_stays: list[list[Any]],
        memory_lens: int = 15
    ) -> None:
        """Initialize memory unit.
        
        Args:
            know_stays: List of known historical stays.
            context_stays: List of recent context stays.
            memory_lens: Number of historical stays to consider.
        """
        self.long_term_memory: dict[str, Any] = {}
        self.short_term_memory: dict[str, Any] = {}
        self.user_profile: str = ""
        self.memory_str_len: int = 1000
        self.memory_lens: int = memory_lens
        
        input_lens = min(len(know_stays), self.memory_lens)
        self.write_memory(known_stays=know_stays[-input_lens:], context_stays=context_stays)

    def write_memory(
        self,
        known_stays: list[list[Any]],
        context_stays: list[list[Any]]
    ) -> None:
        """Process and store stays into memory structures.
        
        Args:
            known_stays: List of known historical stays.
            context_stays: List of recent context stays.
        """
        # Extract first 4 elements from each stay
        known_stays_slim = [traj[:4] for traj in known_stays]
        context_stays_slim = [traj[:4] for traj in context_stays]
        
        # Build venue mapping
        venue_mapping = {entry[-1]: entry[-2] for entry in known_stays_slim}

        # Process long-term memory
        df = pd.DataFrame(
            known_stays_slim,
            columns=['Hour', 'Weekday', 'Venue_Category_Name', 'Venue_ID']
        )

        k = 5
        hour_counts = df['Hour'].value_counts().sort_values(ascending=False)
        top_hours = hour_counts.head(k).reset_index()
        top_hours.columns = ['Hour', 'Count']

        venue_counts = df['Venue_Category_Name'].value_counts().sort_values(ascending=False)
        top_venues = venue_counts.head(k).reset_index()
        top_venues.columns = ['Venue_Category_Name', 'Count']

        hourly_venue_counts = df.groupby(['Hour', 'Venue_Category_Name']).size().reset_index(name='Count')
        hourly_venue_summary = hourly_venue_counts.groupby('Hour').apply(
            lambda x: x.nlargest(1, 'Count')
        ).reset_index(drop=True)

        df['Next_Venue'] = df['Venue_Category_Name'].shift(-1)
        df['Transition'] = df['Venue_Category_Name'] + ' -> ' + df['Next_Venue']
        transition_counts = df['Transition'].value_counts().reset_index()
        transition_counts.columns = ['Transition', 'Count']

        self.long_term_memory = {
            "venue_id_to_name": venue_mapping,
            "top_k_frequent_hours": top_hours.to_dict('records'),
            "top_k_frequent_venues": top_venues.to_dict('records'),
            "hourly_venue_count": hourly_venue_summary.to_dict('records'),
            "activity_transition": transition_counts.to_dict('records')
        }

        # Process short-term memory
        self.short_term_memory = {
            'last_visit': {},
            'frequent_locations': {},
            'visit_times': {}
        }

        for entry in context_stays_slim:
            time, day, location, id_ = entry

            self.short_term_memory['last_visit'] = {
                'time': time,
                'day': day,
                'location': location,
                'venue_id': id_
            }

            if location not in self.short_term_memory['frequent_locations']:
                self.short_term_memory['frequent_locations'][location] = 0
            self.short_term_memory['frequent_locations'][location] += 1

            if day not in self.short_term_memory['visit_times']:
                self.short_term_memory['visit_times'][day] = []
            self.short_term_memory['visit_times'][day].append({
                'time': time,
                'location': location,
                'id': id_
            })

    def memory_compress(self, memory_prompt: str) -> str | None:
        """Compress memory prompt if too long.
        
        Args:
            memory_prompt: Memory prompt string.
            
        Returns:
            Compressed prompt or None if not needed.
        """
        if len(memory_prompt) >= self.memory_str_len * 2:
            return (
                memory_prompt[:self.memory_str_len] +
                "\n......\n" +
                memory_prompt[-self.memory_str_len:]
            )
        return None

    def read_memory(
        self,
        user_id: str,
        target_stay: list[Any]
    ) -> dict[str, Any]:
        """Read and format memory data for prompt generation.
        
        Args:
            user_id: User identifier.
            target_stay: Target stay data.
            
        Returns:
            Dictionary with formatted memory information.
        """
        long_mem_prompt = self.long_term_memory_readout(self.long_term_memory)
        if self.memory_lens == 0:
            compressed = self.memory_compress(long_mem_prompt)
            if compressed:
                long_mem_prompt = compressed
        short_mem_prompt = self.short_term_memory_readout(self.short_term_memory)
        user_profile_prompt = self.user_profile_generation(self.long_term_memory)
        
        return {
            'historical_info': long_mem_prompt,
            'context_info': short_mem_prompt,
            'user_profile': user_profile_prompt,
            'target_stay': target_stay
        }

    @staticmethod
    def long_term_memory_readout(long_mem: dict[str, Any]) -> str:
        """Generate textual readout of long-term memory.
        
        Args:
            long_mem: Long-term memory dictionary.
            
        Returns:
            Formatted memory prompt string.
        """
        venue_id_to_name = long_mem['venue_id_to_name']
        top_k_frequent_hours = long_mem['top_k_frequent_hours']
        top_k_frequent_venues = long_mem['top_k_frequent_venues']
        hourly_venue_count = long_mem['hourly_venue_count']
        activity_transition = long_mem['activity_transition']

        frequent_hours = ", ".join(
            f"{item['Hour']} ({item['Count']} times)"
            for item in top_k_frequent_hours
        )

        frequent_venues = ", ".join(
            f"{item['Venue_Category_Name']} ({item['Count']} times)"
            for item in top_k_frequent_venues
        )

        hourly_activity: dict[str, list[str]] = {}
        for item in hourly_venue_count:
            hour = item['Hour']
            venue = item['Venue_Category_Name']
            count = item['Count']
            if hour not in hourly_activity:
                hourly_activity[hour] = []
            hourly_activity[hour].append(f"{venue} ({count} times)")

        hourly_activity_desc = ", ".join(
            f"{hour}: {', '.join(venues)}"
            for hour, venues in hourly_activity.items()
        )

        transitions = ", ".join(
            f"{item['Transition']} ({item['Count']} times)"
            for item in activity_transition
        )

        return (
            f"place id to name mapping: {venue_id_to_name}. "
            f"In historical stays, The user frequently engages in activities at {frequent_hours}. "
            f"The most frequently visited venues are {frequent_venues}. "
            f"Hourly venue activities include {hourly_activity_desc}. "
            f"The user's activity transitions often include sequences such as {transitions}."
        )

    @staticmethod
    def short_term_memory_readout(memory: dict[str, Any]) -> str:
        """Generate textual readout of short-term memory.
        
        Args:
            memory: Short-term memory dictionary.
            
        Returns:
            Formatted memory prompt string.
        """
        last_visit = memory['last_visit']
        frequent_locations = memory['frequent_locations']
        visit_times = memory['visit_times']

        prompt = (
            f"In recent context Stays, User's last visit was on {last_visit['day']} "
            f"at {last_visit['time']} to {last_visit['location']} (ID: {last_visit['venue_id']}). "
        )
        
        locations_str = ", ".join(
            f"{loc} ({count} times)"
            for loc, count in frequent_locations.items()
        )
        prompt += f"Frequently visited locations include: {locations_str}. "
        
        times_str = "; ".join(
            f"{day}: " + ", ".join(
                f"{entry['time']} at {entry['location']} (ID: {entry['id']})"
                for entry in entries
            )
            for day, entries in visit_times.items()
        )
        prompt += f"Visit times: {times_str}."

        return prompt

    @staticmethod
    def user_profile_generation(long_mem: dict[str, Any]) -> str:
        """Generate user profile from long-term memory.
        
        Args:
            long_mem: Long-term memory dictionary.
            
        Returns:
            Generated user profile string.
        """
        top_k_frequent_hours = long_mem['top_k_frequent_hours']
        top_k_frequent_venues = long_mem['top_k_frequent_venues']

        most_frequent_hour = max(top_k_frequent_hours, key=lambda x: x['Count'])
        most_frequent_venue = max(top_k_frequent_venues, key=lambda x: x['Count'])

        insights: list[str] = []

        # Check activity patterns
        hours_set = {item['Hour'] for item in top_k_frequent_hours}
        venues_set = {item['Venue_Category_Name'] for item in top_k_frequent_venues}

        if hours_set & Memory.EVENING_HOURS:
            insights.append("enjoys evening activities")

        if hours_set & Memory.REGULAR_HOURS:
            insights.append("maintains a regular lifestyle")

        if hours_set & Memory.NIGHTLIFE_HOURS:
            insights.append("enjoys nightlife")

        if venues_set & Memory.COMMUTER_VENUES:
            insights.append("has a fixed commute")

        if venues_set & Memory.LEISURE_VENUES:
            insights.append("enjoys leisure activities")

        if venues_set & Memory.SHOPPING_VENUES:
            insights.append("frequently shops for clothes and cosmetics")

        if venues_set & Memory.HEALTH_VENUES:
            insights.append("is health conscious and regularly visits the gym")

        if venues_set & Memory.FOOD_VENUES:
            insights.append("enjoys trying different types of food and drinks")

        insights_str = ", ".join(insights) if insights else "has diverse interests"
        
        return (
            f"The user is most active at {most_frequent_hour['Hour']} "
            f"with {most_frequent_hour['Count']} visits. "
            f"They frequently visit {most_frequent_venue['Venue_Category_Name']} "
            f"with {most_frequent_venue['Count']} visits."
            f"Based on the data, the user {insights_str}."
        )
