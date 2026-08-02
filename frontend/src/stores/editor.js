import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { addConcept, updateConcept, deleteConcept, addRelation, updateRelation, deleteRelation } from '@/api'

/**
 * 编辑模式 + 撤销/重做。
 * 每个操作压入 { undo, redo } 一对可逆函数，undo/redo 实际调用后端 API，
 * 由工作台在调用后刷新图谱数据。
 */
export const useEditorStore = defineStore('editor', () => {
  const isEditing = ref(false)
  const undoStack = ref([])
  const redoStack = ref([])

  function toggleEdit() {
    isEditing.value = !isEditing.value
    if (!isEditing.value) {
      undoStack.value = []
      redoStack.value = []
    }
  }

  function _push(undoFn, redoFn) {
    undoStack.value.push({ undo: undoFn, redo: redoFn })
    redoStack.value = []
  }

  async function undo() {
    const action = undoStack.value.pop()
    if (!action) return false
    redoStack.value.push(action)
    await action.undo()
    return true
  }

  async function redo() {
    const action = redoStack.value.pop()
    if (!action) return false
    undoStack.value.push(action)
    await action.redo()
    return true
  }

  // ── 概念 ──

  async function createConcept(paperId, data) {
    const result = await addConcept(paperId, data) // 返回 { slug }
    const payload = { name: data.name, definition: data.definition || '', type: data.type || 'finding', page: data.page || 1 }
    _push(
      async () => { await deleteConcept(paperId, result.slug) },
      async () => { await addConcept(paperId, payload) } // slug 由后端按 name 确定性生成，可还原
    )
    return result
  }

  async function editConcept(paperId, slug, data, oldData) {
    await updateConcept(paperId, slug, data)
    _push(
      async () => { await updateConcept(paperId, slug, oldData) },
      async () => { await updateConcept(paperId, slug, data) }
    )
  }

  async function removeConcept(paperId, slug, oldConcept) {
    await deleteConcept(paperId, slug)
    const payload = {
      name: oldConcept.name, definition: oldConcept.definition || '',
      type: oldConcept.type || 'finding', page: oldConcept.page || 1,
    }
    _push(
      async () => { await addConcept(paperId, payload) },
      async () => { await deleteConcept(paperId, slug) }
    )
  }

  // ── 关系 ──

  async function createRelation(paperId, data) {
    const result = await addRelation(paperId, data) // 返回 { id }
    _push(
      async () => { await deleteRelation(paperId, result.id) },
      async () => { await addRelation(paperId, data) } // 新 id 不同，但数据可还原
    )
    return result
  }

  async function editRelation(paperId, id, data, oldData) {
    await updateRelation(paperId, id, data)
    _push(
      async () => { await updateRelation(paperId, id, oldData) },
      async () => { await updateRelation(paperId, id, data) }
    )
  }

  async function removeRelation(paperId, id, oldLink) {
    await deleteRelation(paperId, id)
    _push(
      async () => {
        await addRelation(paperId, {
          source_slug: oldLink.source, target_slug: oldLink.target,
          type: oldLink.type || 'cites', evidence: oldLink.evidence || '',
        })
      },
      async () => { await deleteRelation(paperId, id) }
    )
  }

  const canUndo = computed(() => undoStack.value.length > 0)
  const canRedo = computed(() => redoStack.value.length > 0)

  return {
    isEditing, canUndo, canRedo,
    toggleEdit, undo, redo,
    createConcept, editConcept, removeConcept,
    createRelation, editRelation, removeRelation,
  }
})
