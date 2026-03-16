import React, { useState } from 'react';
import { StyleSheet, Pressable, View } from 'react-native';
import { Text, Surface } from 'react-native-paper';

interface MedicalTermTooltipProps {
  term: string;
  explanation: string;
}

export function MedicalTermTooltip({ term, explanation }: MedicalTermTooltipProps) {
  const [isExpanded, setIsExpanded] = useState(false);

  return (
    <View style={styles.container}>
      <Pressable onPress={() => setIsExpanded(!isExpanded)}>
        <Text style={styles.term}>{term}</Text>
      </Pressable>
      {isExpanded && (
        <Surface style={styles.tooltip} elevation={2}>
          <Text variant="bodySmall" style={styles.explanation}>
            {explanation}
          </Text>
        </Surface>
      )}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    marginVertical: 2,
  },
  term: {
    color: '#1976d2',
    textDecorationLine: 'underline',
    fontWeight: '600',
  },
  tooltip: {
    padding: 12,
    borderRadius: 8,
    marginTop: 4,
    marginBottom: 4,
    backgroundColor: '#e3f2fd',
  },
  explanation: {
    color: '#333',
  },
});
